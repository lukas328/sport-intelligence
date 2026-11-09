# Role classifier (research, not shipped)

Player / goalkeeper / referee from a person crop, trained on Roboflow handball sets with role boxes
(all CC BY 4.0: chandan-basti/handball_player_detection v2, spin-sight/handball-players v1,
gergely-fazekas-cusi4/handball-1pgwr v10, yolohandball/custom_handball_dataset v5; the set
handballdetectionvictorcollado/handball-detection-fj8rc v2 is held out as unseen halls).
ResNet18 (ImageNet), 64x128 crops, balanced batches (`make_crops.py`, `train_roles.py`).

| Held-out halls, single crop | Recall | Precision |
|---|---|---|
| Player | 97 % | 93 % |
| Goalkeeper | 67 % | 86 % |
| Referee | 69 % | 82 % |

On our clips (`apply_frames.py`) goalkeepers at their goal and real referees are found, but players
in dark kits are often taken for referees. Next: vote over a whole track and combine with what the
pipeline knows (at most two referees whose colour differs from both teams, one goalkeeper per team
near its goal) before it replaces the colour and position rules.
