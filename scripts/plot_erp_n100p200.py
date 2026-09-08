#!/usr/bin/env python3
"""
Visualisation des potentiels évoqués auditifs (N100-P200), alignés sur le
début de chaque stimulation, à partir d'un enregistrement EEG type OpenBCI.

Pipeline :
  1) lecture du CSV (avec ou sans en-tête, colonnes fixées ci-dessous)
  2) filtrage passe-bande (Butterworth, zero-phase) sur le signal continu
  3) détection des tops TTL (apparition des sons) sur la colonne trigger
  4) découpage en essais ("epochs") autour de chaque top, correction de ligne
     de base, rejet des essais trop bruités (artefacts)
  5) moyenne (grand average) ± erreur standard, et affichage

Dépendances : numpy, pandas, scipy, matplotlib
"""

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt

# =================================================================
# PARAMÈTRES — à adapter à votre enregistrement
# =================================================================
CSV_PATH = "openbci_simulated_N100P200_sans_entete.csv"
# CSV_PATH="BrainFlow-RAW_2026-09-08_10-47-23_11.csv"  # chemin vers le CSV à analyser
HAS_HEADER = False          # True si le fichier a une ligne de noms de colonnes

FS = 250                    # Hz, fréquence d'échantillonnage

# Colonnes (index 0-based). Avec le format "sans entête" convenu précédemment :
# colonne 13 (1-indexée) = index 12 (0-indexée) = TTL
TTL_COL = 13
EEG_COLS = [1, 2, 3, 4, 5, 6, 7, 8]   # EXG Channel 0..7
CHANNEL_NAMES = [f"Ch{i}" for i in range(len(EEG_COLS))]
CHANNEL_TO_PLOT = 1          # index dans EEG_COLS/CHANNEL_NAMES à afficher en détail (ici "Ch1" ~ Cz)

# Filtrage passe-bande (Hz) — classique pour un ERP cortical N100-P200
FILT_LOW = 1.0
FILT_HIGH = 30.0
FILT_ORDER = 4

# Fenêtre d'epoching (secondes autour de chaque top TTL)
T_MIN = -0.10
T_MAX = 0.50
BASELINE = (-0.10, 0.0)     # fenêtre de correction de ligne de base

# Détection des tops TTL
TTL_THRESHOLD = 0.5

# Rejet d'artefacts : amplitude crête-à-crête max tolérée par essai (µV)
REJECT_PTP_UV = 150.0

OUT_FIG_DETAIL = "erp_n100_p200_detail.png"
OUT_FIG_GRID = "erp_n100_p200_tous_canaux.png"


# =================================================================
# FONCTIONS
# =================================================================
def load_raw(csv_path, has_header):
    """Charge le CSV en ignorant d'éventuelles lignes de métadonnées '%...'."""
    with open(csv_path, "r") as f:
        first_line = f.readline()
    skiprows = 0
    if first_line.startswith("%"):
        # compte les lignes de métadonnées commençant par '%'
        with open(csv_path, "r") as f:
            for line in f:
                if line.startswith("%"):
                    skiprows += 1
                else:
                    break
    df = pd.read_csv(csv_path, header=0 if has_header else None, skiprows=skiprows)
    return df  # on ne convertit pas tout en float : certaines colonnes (ex. timestamp
               # formaté) sont du texte ; seules les colonnes utilisées sont castées ensuite


def bandpass_filter(signal, fs, low, high, order=4):
    """Filtre passe-bande Butterworth, zero-phase (filtfilt)."""
    nyq = fs / 2.0
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal)


def detect_ttl_onsets(ttl_signal, threshold=0.5):
    """Détecte les fronts montants du signal TTL (indices d'échantillon)."""
    above = ttl_signal > threshold
    onsets = np.where(above[1:] & ~above[:-1])[0] + 1
    return onsets


def epoch_signal(signal, onsets, fs, t_min, t_max):
    """Découpe le signal continu en essais autour de chaque onset."""
    n_pre = int(round(-t_min * fs))
    n_post = int(round(t_max * fs))
    n_samples_epoch = n_pre + n_post
    epochs = []
    kept_onsets = []
    for onset in onsets:
        start = onset - n_pre
        end = onset + n_post
        if start < 0 or end > len(signal):
            continue  # essai tronqué en bord d'enregistrement -> ignoré
        epochs.append(signal[start:end])
        kept_onsets.append(onset)
    times = (np.arange(n_samples_epoch) - n_pre) / fs
    return np.array(epochs), times, np.array(kept_onsets)


def baseline_correct(epochs, times, baseline):
    """Soustrait la moyenne de la fenêtre de baseline à chaque essai."""
    mask = (times >= baseline[0]) & (times < baseline[1])
    baselines = epochs[:, mask].mean(axis=1, keepdims=True)
    return epochs - baselines


def reject_bad_epochs(epochs, ptp_max_uv):
    """Retourne un masque booléen des essais dont l'amplitude crête-à-crête
    reste sous le seuil (rejet simple des artefacts type clignement)."""
    ptp = epochs.max(axis=1) - epochs.min(axis=1)
    return ptp <= ptp_max_uv


def find_peak(times, waveform, t_lo, t_hi, mode="min"):
    """Cherche le pic (min ou max) de la forme d'onde dans une fenêtre temporelle."""
    mask = (times >= t_lo) & (times <= t_hi)
    idx_local = np.argmin(waveform[mask]) if mode == "min" else np.argmax(waveform[mask])
    idx_global = np.where(mask)[0][idx_local]
    return times[idx_global], waveform[idx_global]


# =================================================================
# TRAITEMENT
# =================================================================
def process_channel(eeg_continuous, onsets):
    """Filtre un canal continu puis produit les essais moyennés + rejetés."""
    filtered = bandpass_filter(eeg_continuous, FS, FILT_LOW, FILT_HIGH, FILT_ORDER)
    epochs, times, _ = epoch_signal(filtered, onsets, FS, T_MIN, T_MAX)
    epochs = baseline_correct(epochs, times, BASELINE)
    good = reject_bad_epochs(epochs, REJECT_PTP_UV)
    epochs_clean = epochs[good]
    grand_avg = epochs_clean.mean(axis=0)
    sem = epochs_clean.std(axis=0, ddof=1) / np.sqrt(epochs_clean.shape[0])
    return times, epochs, epochs_clean, grand_avg, sem, good


def main():
    raw = load_raw(CSV_PATH, HAS_HEADER)
    ttl = raw.iloc[:, TTL_COL].to_numpy(dtype=float)
    onsets = detect_ttl_onsets(ttl, TTL_THRESHOLD)
    print(f"Tops TTL détectés : {len(onsets)}")

    # --- traitement de tous les canaux EEG demandés ---
    results = {}
    for name, col in zip(CHANNEL_NAMES, EEG_COLS):
        eeg_continuous = raw.iloc[:, col].to_numpy(dtype=float)
        results[name] = process_channel(eeg_continuous, onsets)
        n_total = results[name][1].shape[0]
        n_kept = results[name][2].shape[0]
        print(f"  {name} : {n_kept}/{n_total} essais conservés après rejet d'artefacts")

    # =============================================================
    # FIGURE 1 — canal choisi, en détail
    # =============================================================
    name = CHANNEL_NAMES[CHANNEL_TO_PLOT]
    times, epochs, epochs_clean, grand_avg, sem, good = results[name]
    t_ms = times * 1000

    fig, ax = plt.subplots(figsize=(8, 5))

    # essais individuels (contexte visuel, discrets)
    for ep in epochs_clean:
        ax.plot(t_ms, ep, color="#9AA5B1", linewidth=0.5, alpha=0.25)

    # bande d'erreur standard
    ax.fill_between(t_ms, (grand_avg - sem) * 1, (grand_avg + sem) * 1,
                     color="#2E6F95", alpha=0.25, linewidth=0, label="Moyenne ± SEM")

    # moyenne (grand average)
    ax.plot(t_ms, grand_avg, color="#1B4965", linewidth=2, label=f"Moyenne ({name}, n={epochs_clean.shape[0]})")

    # repères
    ax.axvline(0, color="#333333", linestyle="--", linewidth=1)
    ax.axhline(0, color="#CCCCCC", linewidth=0.8)
    ax.text(0, ax.get_ylim()[1] * 0.95, " Stimulus", color="#333333", fontsize=9, va="top")

    # annotation automatique des pics N100 / P200
    t_n1, a_n1 = find_peak(times, grand_avg, 0.06, 0.15, mode="min")
    t_p2, a_p2 = find_peak(times, grand_avg, 0.14, 0.26, mode="max")
    ax.plot(t_n1 * 1000, a_n1, "o", color="#C0392B", markersize=6)
    ax.annotate(f"N100\n{t_n1*1000:.0f} ms, {a_n1:.1f} µV",
                xy=(t_n1 * 1000, a_n1), xytext=(t_n1 * 1000 - 15, a_n1 - 3),
                fontsize=9, color="#C0392B")
    ax.plot(t_p2 * 1000, a_p2, "o", color="#B7791F", markersize=6)
    ax.annotate(f"P200\n{t_p2*1000:.0f} ms, {a_p2:.1f} µV",
                xy=(t_p2 * 1000, a_p2), xytext=(t_p2 * 1000 + 5, a_p2 + 3),
                fontsize=9, color="#B7791F")

    ax.set_xlabel("Temps depuis le stimulus (ms)")
    ax.set_ylabel("Amplitude (µV)")
    ax.set_title(f"Potentiel évoqué auditif — {name} (filtré {FILT_LOW}-{FILT_HIGH} Hz)")
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, color="#EEEEEE", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(OUT_FIG_DETAIL, dpi=150)
    print(f"Figure détaillée enregistrée : {OUT_FIG_DETAIL}")

    # =============================================================
    # FIGURE 2 — vue d'ensemble, petits multiples pour tous les canaux
    # =============================================================
    n_ch = len(CHANNEL_NAMES)
    n_cols = 4
    n_rows = int(np.ceil(n_ch / n_cols))
    fig2, axes = plt.subplots(n_rows, n_cols, figsize=(4 * n_cols, 3 * n_rows), sharex=True, sharey=True)
    axes = np.array(axes).reshape(-1)

    for i, name in enumerate(CHANNEL_NAMES):
        ax = axes[i]
        times, _, epochs_clean, grand_avg, sem, _ = results[name]
        t_ms = times * 1000
        ax.fill_between(t_ms, grand_avg - sem, grand_avg + sem, color="#2E6F95", alpha=0.25, linewidth=0)
        ax.plot(t_ms, grand_avg, color="#1B4965", linewidth=1.5)
        ax.axvline(0, color="#999999", linestyle="--", linewidth=0.8)
        ax.axhline(0, color="#DDDDDD", linewidth=0.6)
        ax.set_title(name, fontsize=10)
        ax.spines[["top", "right"]].set_visible(False)

    for j in range(n_ch, len(axes)):
        axes[j].axis("off")

    fig2.supxlabel("Temps depuis le stimulus (ms)")
    fig2.supylabel("Amplitude (µV)")
    fig2.suptitle(f"Potentiels évoqués auditifs par canal (filtré {FILT_LOW}-{FILT_HIGH} Hz)")
    fig2.tight_layout()
    fig2.savefig(OUT_FIG_GRID, dpi=150)
    print(f"Figure vue d'ensemble enregistrée : {OUT_FIG_GRID}")

    plt.show()


if __name__ == "__main__":
    main()
