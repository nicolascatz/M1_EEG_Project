# -*- coding: utf-8 -*-
"""
Oddball auditif simple (PsychoPy) - sans Arduino ni EEG.
Sons standards (fréquents) et déviants (rares), avec option
de détection au clavier (barre espace) pour les déviants.
"""

from psychopy import visual, core, event, sound, data, gui
import random
import os

# =========================================================
# PARAMÈTRES
# =========================================================
N_TRIALS = 200
P_ODDBALL = 0.20

FREQ_STANDARD = 1000     # Hz
FREQ_ODDBALL = 2000      # Hz
TONE_DUR = 0.10          # s
ISI_MIN = 0.8            # s
ISI_MAX = 1.2            # s
RESPONSE_WINDOW = 1.0    # s
TASK = "passive"         # "passive" ou "detect"

# =========================================================
# BOÎTE DE DIALOGUE SUJET
# =========================================================
info = {"Sujet": "001", "Session": "01"}
dlg = gui.DlgFromDict(info, title="Oddball auditif")
if not dlg.OK:
    core.quit()

os.makedirs("data", exist_ok=True)
filename = os.path.join("data", f"sub-{info['Sujet']}_ses-{info['Session']}_oddball")

# =========================================================
# FENÊTRE ET STIMULI
# =========================================================
win = visual.Window(size=(800, 600), color="black", units="norm", fullscr=False)
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
# SÉQUENCE DE STIMULI
# =========================================================
def build_sequence(n_trials, p_oddball, max_consecutive_oddball=1):
    n_odd = int(round(n_trials * p_oddball))
    n_std = n_trials - n_odd
    seq = [0] * n_std + [1] * n_odd
    while True:
        random.shuffle(seq)
        if seq[0] == 1:
            continue
        ok, run = True, 0
        for v in seq:
            run = run + 1 if v == 1 else 0
            if run > max_consecutive_oddball:
                ok = False
                break
        if ok:
            return seq

sequence = build_sequence(N_TRIALS, P_ODDBALL)

# =========================================================
# GESTION DES DONNÉES
# =========================================================
exp = data.ExperimentHandler(name="oddball_auditif", extraInfo=info, dataFileName=filename)
global_clock = core.Clock()
resp_clock = core.Clock()

# =========================================================
# INSTRUCTIONS
# =========================================================
instructions.draw()
win.flip()
event.waitKeys()
fixation.draw()
win.flip()
core.wait(1.0)

# =========================================================
# BOUCLE D'ESSAIS
# =========================================================
for trial_idx, is_oddball in enumerate(sequence):

    stim = tone_oddball if is_oddball else tone_standard

    event.clearEvents()
    resp_clock.reset()

    stim.play()
    onset_time = global_clock.getTime()

    responded, rt = False, None

    if TASK == "detect":
        keys = event.waitKeys(maxWait=RESPONSE_WINDOW, keyList=["space", "escape"],
                               timeStamped=resp_clock)
        if keys:
            key, rt = keys[0]
            if key == "escape":
                break
            responded = True
    else:
        core.wait(RESPONSE_WINDOW)
        if event.getKeys(["escape"]):
            break

    isi = random.uniform(ISI_MIN, ISI_MAX)
    core.wait(isi)

    exp.addData("trial", trial_idx)
    exp.addData("stim_type", "oddball" if is_oddball else "standard")
    exp.addData("onset_time", onset_time)
    exp.addData("responded", responded)
    exp.addData("rt", rt)
    exp.nextEntry()

# =========================================================
# FIN
# =========================================================
goodbye = visual.TextStim(win, text="Fin de l'expérience.\nMerci !",
                           color="white", height=0.08)
goodbye.draw()
win.flip()
core.wait(2.0)

exp.saveAsWideText(filename + ".csv")

win.close()
core.quit()
