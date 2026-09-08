# -*- coding: utf-8 -*-
"""
Paradigme d'oddball auditif (PsychoPy) avec envoi de triggers TTL
via Arduino, synchronisés à l'acquisition EEG OpenBCI (Cyton).

Principe de synchronisation :
- Le PC envoie un octet (code) à l'Arduino via USB/série au moment exact
  de l'apparition du son.
- L'Arduino encode ce code en binaire sur 3 broches numériques
  (D2, D3, D4 sur l'Arduino) reliées aux broches d'entrée numériques
  du Cyton (D11, D12, D13 par défaut), le tout référencé à la masse (GND).
- Le pattern binaire reste actif ~10 ms puis revient à 0.
- Dans OpenBCI GUI, activer "Digital Read" pour voir les marqueurs
  enregistrés en même temps que l'EEG (canaux D11/D12/D13).

Codes utilisés ici :
  1 = son standard
  2 = son déviant (oddball)
  3 = réponse du sujet (bouton pressé)
  6 = début de l'expérience
  7 = fin de l'expérience

Câblage Arduino -> Cyton :
  Arduino D2 -> Cyton D11
  Arduino D3 -> Cyton D12
  Arduino D4 -> Cyton D13
  Arduino GND -> Cyton GND

Voir le sketch Arduino fourni séparément (oddball_trigger.ino).
"""

from psychopy import visual, core, event, sound, data, gui
import numpy as np
import random
import serial
import time
import os

# =========================================================
# 1. PARAMÈTRES DE L'EXPÉRIENCE
# =========================================================
N_TRIALS = 200            # nombre total de sons
P_ODDBALL = 0.20          # proportion de déviants (20%)
FREQ_STANDARD = 1000      # Hz
FREQ_ODDBALL = 2000       # Hz
TONE_DUR = 0.10           # durée du son (s)
ISI_MIN = 0.8             # intervalle inter-stimulus min (s)
ISI_MAX = 1.2             # intervalle inter-stimulus max (s)
RESPONSE_WINDOW = 1.0     # fenêtre de réponse après le son (s)
TASK = "passive"          # "passive" (rien à faire) ou "detect" (bouton sur oddball)

SERIAL_PORT = "COM3"      # à adapter (ex: "/dev/ttyACM0" sous Linux/Mac)
BAUDRATE = 115200
TRIGGER_PULSE_MS = 10     # doit correspondre à la durée codée côté Arduino

CODE_STANDARD = 1
CODE_ODDBALL = 2
CODE_RESPONSE = 3
CODE_START = 6
CODE_END = 7

# =========================================================
# 2. BOÎTE DE DIALOGUE SUJET
# =========================================================
info = {"Sujet": "001", "Session": "01"}
dlg = gui.DlgFromDict(info, title="Oddball auditif")
if not dlg.OK:
    core.quit()

data_dir = "data"
os.makedirs(data_dir, exist_ok=True)
filename = os.path.join(
    data_dir, f"sub-{info['Sujet']}_ses-{info['Session']}_oddball"
)

# =========================================================
# 3. CONNEXION SÉRIE À L'ARDUINO
# =========================================================
try:
    arduino = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0)
    time.sleep(2)  # laisser le temps à l'Arduino de rebooter après ouverture du port
    print(f"Arduino connecté sur {SERIAL_PORT}")
except Exception as e:
    print(f"ATTENTION : Arduino non connecté ({e}). Mode simulation (pas de triggers).")
    arduino = None


def send_trigger(code):
    """Envoie un code de trigger à l'Arduino (1 octet)."""
    if arduino is not None:
        try:
            arduino.write(bytes([code]))
        except Exception as e:
            print(f"Erreur envoi trigger : {e}")
    # Toujours logger le trigger avec un timestamp précis, même sans Arduino
    log_trigger(code)


trigger_log = []


def log_trigger(code):
    trigger_log.append((core.getTime(), code))


# =========================================================
# 4. FENÊTRE ET STIMULI
# =========================================================
win = visual.Window(
    size=(800, 600), color="black", units="norm", fullscr=False
)
fixation = visual.TextStim(win, text="+", color="white", height=0.1)
instructions_txt = (
    "Vous allez entendre une série de sons.\n\n"
    + ("Appuyez sur ESPACE dès que vous entendez le son AIGU (rare).\n\n"
       if TASK == "detect" else
       "Restez détendu et fixez la croix, aucune réponse n'est requise.\n\n")
    + "Appuyez sur une touche pour commencer."
)
instructions = visual.TextStim(win, text=instructions_txt, color="white",
                                height=0.05, wrapWidth=1.6)

tone_standard = sound.Sound(value=FREQ_STANDARD, secs=TONE_DUR, stereo=True)
tone_oddball = sound.Sound(value=FREQ_ODDBALL, secs=TONE_DUR, stereo=True)

# =========================================================
# 5. CONSTRUCTION DE LA SÉQUENCE DE STIMULI
# =========================================================
def build_sequence(n_trials, p_oddball, max_consecutive_oddball=1):
    """Construit une séquence pseudo-aléatoire de standards (0) et oddballs (1),
    sans dépasser 'max_consecutive_oddball' déviants consécutifs,
    et en évitant un oddball comme tout premier essai."""
    n_odd = int(round(n_trials * p_oddball))
    n_std = n_trials - n_odd
    seq = [0] * n_std + [1] * n_odd

    while True:
        random.shuffle(seq)
        if seq[0] == 1:
            continue
        ok = True
        run = 0
        for v in seq:
            run = run + 1 if v == 1 else 0
            if run > max_consecutive_oddball:
                ok = False
                break
        if ok:
            return seq


sequence = build_sequence(N_TRIALS, P_ODDBALL)

# =========================================================
# 6. GESTION DES DONNÉES (ExperimentHandler)
# =========================================================
exp = data.ExperimentHandler(
    name="oddball_auditif",
    extraInfo=info,
    dataFileName=filename,
)

global_clock = core.Clock()
resp_clock = core.Clock()

# =========================================================
# 7. INSTRUCTIONS
# =========================================================
instructions.draw()
win.flip()
event.waitKeys()
fixation.draw()
win.flip()
core.wait(1.0)

send_trigger(CODE_START)

# =========================================================
# 8. BOUCLE D'ESSAIS
# =========================================================
for trial_idx, is_oddball in enumerate(sequence):

    stim = tone_oddball if is_oddball else tone_standard
    code = CODE_ODDBALL if is_oddball else CODE_STANDARD

    event.clearEvents()
    resp_clock.reset()

    # Onset synchronisé : trigger envoyé juste avant/à .play()
    stim.play()
    send_trigger(code)
    onset_time = global_clock.getTime()

    responded = False
    rt = None

    if TASK == "detect":
        keys = event.waitKeys(
            maxWait=RESPONSE_WINDOW, keyList=["space", "escape"],
            timeStamped=resp_clock
        )
        if keys:
            key, rt = keys[0]
            if key == "escape":
                break
            responded = True
            send_trigger(CODE_RESPONSE)
    else:
        core.wait(RESPONSE_WINDOW)
        if event.getKeys(["escape"]):
            break

    # ISI jitterée (temps restant après la fenêtre de réponse)
    isi = random.uniform(ISI_MIN, ISI_MAX)
    core.wait(isi)

    exp.addData("trial", trial_idx)
    exp.addData("stim_type", "oddball" if is_oddball else "standard")
    exp.addData("trigger_code", code)
    exp.addData("onset_time", onset_time)
    exp.addData("responded", responded)
    exp.addData("rt", rt)
    exp.nextEntry()

# =========================================================
# 9. FIN DE L'EXPÉRIENCE
# =========================================================
send_trigger(CODE_END)

goodbye = visual.TextStim(win, text="Fin de l'expérience.\nMerci !",
                           color="white", height=0.08)
goodbye.draw()
win.flip()
core.wait(2.0)

exp.saveAsWideText(filename + ".csv")

# Sauvegarde du log de triggers (utile pour vérifier l'alignement a posteriori)
with open(filename + "_triggers.csv", "w") as f:
    f.write("timestamp,code\n")
    for t, c in trigger_log:
        f.write(f"{t},{c}\n")

if arduino is not None:
    arduino.close()

win.close()
core.quit()
