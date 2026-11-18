-- After the clean-up: what is left of the review's traces (read only).
SELECT count(*) AS plays_left FROM plays WHERE id = '52a42916-cdfd-4b17-b1ea-6f81eb9068e7';
SELECT count(*) AS collections_left FROM collections WHERE id = 'b4cb9ad4-42dc-4d18-8f39-3de843de2013';
SELECT settings->'team_features' AS team_features FROM teams WHERE id = '13d6190c-4fc3-440c-a647-42375a237b57';
