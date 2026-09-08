#!/usr/bin/env python3
"""
Génère un enregistrement EEG simulé, au format OpenBCI/BrainFlow brut
(sans en-tête, délimiteur tabulation, 24 colonnes), contenant un potentiel
évoqué auditif N100-P200 sur 8 canaux EEG.

Colonnes du fichier généré (0-indexées) :
  0        : index d'échantillon
  1-8      : canaux EEG 1 à 8 (µV)
  9-11     : accéléromètre x, y, z (quasi nul, non simulé)
  12       : TTL / trigger de stimulation -> colonne 13 en 1-indexé
  13-21    : colonnes auxiliaires/digitales (non utilisées, mises à 0)
  22       : timestamp Unix (s)
  23       : marqueur (non utilisé, mis à 0)

Chaque top TTL dure 5 ms (arrondi à l'échantillon le plus proche à 250 Hz).
"""

import time

import numpy as np
import pandas as pd

# ------------------------------------------------------------------
# Paramètres
# ------------------------------------------------------------------
FS = 250                      # Hz, fréquence d'échantillonnage (OpenBCI Cyton)
DURATION_S = 180              # durée totale de l'enregistrement (s)
N_SAMPLES = int(DURATION_S * FS)

N_EEG_CHANNELS = 8
TTL_COL = 12                  # index 0-based -> colonne 13 (1-indexée)
TTL_PULSE_S = 0.005           # durée du pulse TTL : 5 ms
TTL_PULSE_SAMPLES = max(1, round(TTL_PULSE_S * FS))

ISI_MIN_S, ISI_MAX_S = 0.8, 1.2   # intervalle inter-stimulus, jitter aléatoire
FIRST_STIM_S = 2.0                # premier stimulus après 2 s (marge pour la baseline)
LAST_MARGIN_S = 1.0               # marge en fin d'enregistrement

# Forme du potentiel évoqué (N100 négatif, P200 positif), en µV,
# temps exprimé en secondes depuis le stimulus
N100_LATENCY, N100_WIDTH, N100_AMP = 0.100, 0.015, 8.0
P200_LATENCY, P200_WIDTH, P200_AMP = 0.200, 0.025, 6.0

# Amplitude relative de l'ERP par canal (topographie fronto-centrale simulée :
# canal 3 = le plus fort, canaux latéraux = plus faibles)
CHANNEL_ERP_SCALE = np.array([0.5, 0.7, 1.0, 0.9, 0.6, 0.8, 0.6, 0.4])

BACKGROUND_STD_UV = 20.0      # écart-type du bruit de fond EEG (µV)
ALPHA_AMP_UV = 8.0            # amplitude du rythme alpha de fond (~10 Hz)
LINE_NOISE_AMP_UV = 3.0       # amplitude résiduelle de bruit secteur (50 Hz)

OUTPUT_PATH = "data/openbci_simulated_N100P200_tab_sans_entete.csv"

RNG = np.random.default_rng(42)


def make_pink_noise(n, std=1.0):
    """Bruit ~1/f (approximation simple par filtrage du bruit blanc en fréquence)."""
    white = RNG.standard_normal(n)
    f = np.fft.rfftfreq(n)
    f[0] = f[1]  # éviter la division par zéro à la fréquence continue
    spectrum = np.fft.rfft(white) / np.sqrt(f)
    pink = np.fft.irfft(spectrum, n)
    return pink / pink.std() * std


def erp_waveform(t):
    """Forme d'onde N100-P200 (µV) en fonction du temps depuis le stimulus (s)."""
    n100 = -N100_AMP * np.exp(-0.5 * ((t - N100_LATENCY) / N100_WIDTH) ** 2)
    p200 = P200_AMP * np.exp(-0.5 * ((t - P200_LATENCY) / P200_WIDTH) ** 2)
    return n100 + p200


def main():
    # --- génération des onsets de stimulation (jitter aléatoire) ---
    onsets_s = []
    t = FIRST_STIM_S
    while t < DURATION_S - LAST_MARGIN_S:
        onsets_s.append(t)
        t += RNG.uniform(ISI_MIN_S, ISI_MAX_S)
    onsets_samples = np.round(np.array(onsets_s) * FS).astype(int)
    print(f"Nombre de stimulations générées : {len(onsets_samples)}")

    time_vec = np.arange(N_SAMPLES) / FS

    # --- canal TTL (colonne 13 / index 12) ---
    ttl = np.zeros(N_SAMPLES)
    for onset in onsets_samples:
        ttl[onset:onset + TTL_PULSE_SAMPLES] = 1

    # --- canaux EEG : bruit de fond (1/f + alpha + secteur) + ERP superposé ---
    eeg = np.zeros((N_SAMPLES, N_EEG_CHANNELS))
    pre = int(0.05 * FS)
    post = int(0.5 * FS)
    for ch in range(N_EEG_CHANNELS):
        background = make_pink_noise(N_SAMPLES, std=BACKGROUND_STD_UV)
        alpha = ALPHA_AMP_UV * np.sin(2 * np.pi * 10 * time_vec + RNG.uniform(0, 2 * np.pi))
        line_noise = LINE_NOISE_AMP_UV * np.sin(2 * np.pi * 50 * time_vec)
        signal = background + alpha + line_noise

        for onset in onsets_samples:
            trial_gain = RNG.normal(1.0, 0.3)  # variabilité essai-à-essai
            start, end = max(0, onset - pre), min(N_SAMPLES, onset + post)
            t_rel = (np.arange(start, end) - onset) / FS
            signal[start:end] += trial_gain * CHANNEL_ERP_SCALE[ch] * erp_waveform(t_rel)

        eeg[:, ch] = signal

    # --- colonnes accessoires (accéléromètre, auxiliaires) : quasi nulles ---
    accel = RNG.normal(0, 0.01, size=(N_SAMPLES, 3))
    aux = np.zeros((N_SAMPLES, 9))          # colonnes 13 à 21
    marker = np.zeros(N_SAMPLES)            # colonne 23
    timestamp = time.time() + time_vec      # colonne 22

    columns = [np.arange(N_SAMPLES)]
    columns += [eeg[:, ch] for ch in range(N_EEG_CHANNELS)]
    columns += [accel[:, 0], accel[:, 1], accel[:, 2]]
    columns += [ttl]
    columns += [aux[:, i] for i in range(aux.shape[1])]
    columns += [timestamp, marker]

    df = pd.DataFrame(np.column_stack(columns))
    df.to_csv(OUTPUT_PATH, sep="\t", header=False, index=False)

    print(f"Fichier écrit : {OUTPUT_PATH}  ({df.shape[0]} lignes x {df.shape[1]} colonnes)")
    print(f"TTL : colonne {TTL_COL + 1} (1-indexée) = index {TTL_COL}, "
          f"pulse de {TTL_PULSE_SAMPLES} échantillon(s) (~{TTL_PULSE_SAMPLES / FS * 1000:.1f} ms à {FS} Hz)")


if __name__ == "__main__":
    main()
