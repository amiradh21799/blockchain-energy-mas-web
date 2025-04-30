import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import LearningRateScheduler
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# --------------------------------------------------------------------------------
# 1) CHARGEMENT DES DONNÉES DE PRÉVISIONS (df_prev)
# --------------------------------------------------------------------------------
file_path = 'pv_prev_meteo_clean.csv'
df_prev = pd.read_csv(file_path)

# Convertir 'Date' en datetime *avec* UTC, puis enlever le fuseau (tz_localize(None))
# => timestamps tz-naive pour éviter l'erreur de comparaison tz-aware vs tz-naive
df_prev['Date'] = pd.to_datetime(df_prev['Date'], errors='coerce', utc=True)
df_prev['Date'] = df_prev['Date'].dt.tz_localize(None)

# (Optionnel) Filtrer entre 2021 et 2024
df_prev = df_prev[(df_prev['Date'] >= '2021-01-01') & (df_prev['Date'] < '2024-09-13')]

# --------------------------------------------------------------------------------
# 2) CHARGEMENT DES DONNÉES HISTORIQUES PV (df_hist)
# --------------------------------------------------------------------------------
file_path_hist = 'pv_historiques_clean.csv'
df_hist = pd.read_csv(file_path_hist)

# Nettoyage si nécessaire
df_hist['Quality'] = df_hist['Quality'].apply(
    lambda x: f"{int(x):02}" if pd.notna(x) and str(x).isdigit() else "NaN"
)
df_hist['name'] = df_hist['name'].replace('Meteorological_Actuals_Data', 'PV_Data')

# Convertir 'Date' en datetime (UTC) puis tz-naive
df_hist['Date'] = pd.to_datetime(df_hist['Date'], errors='coerce', utc=True)
df_hist['Date'] = df_hist['Date'].dt.tz_localize(None)

# (Optionnel) Filtrer entre 2021 et 2024
df_hist = df_hist[(df_hist['Date'] >= '2021-01-01') & (df_hist['Date'] <= '2024-12-31')]

# Convertir en float les colonnes PV
df_hist['Ptot_HEI_PV'] = pd.to_numeric(df_hist['Ptot_HEI_PV'], errors='coerce')
df_hist['Ptot_RIZOMM_PV'] = pd.to_numeric(df_hist['Ptot_RIZOMM_PV'], errors='coerce')

# --------------------------------------------------------------------------------
# 3) RÉSAMPLE HORAIRE ET CALCUL PRODUCTION TOTALE
# --------------------------------------------------------------------------------
df_prev_numeric = (
    df_prev
    .set_index('Date')
    .select_dtypes(include=['number'])  # colonnes numériques
    .resample('h').mean()
    .reset_index()
)

df_hist_numeric = (
    df_hist
    .set_index('Date')
    .select_dtypes(include=['number'])
    .resample('h').mean()
    .reset_index()
)

# Production PV totale
df_hist_numeric['PV_Total'] = df_hist_numeric[['Ptot_RIZOMM_PV', 'Ptot_HEI_PV']].sum(axis=1)

# --------------------------------------------------------------------------------
# 4) PRÉPARATION DES FEATURES & MERGE
# --------------------------------------------------------------------------------

# Colonnes météo (à adapter selon votre dataset)
meteorological_variables = [
    'AirTemp', 'CloudOpacity', 'Dni10', 'Dni90', 'DniMoy',
    'Ghi10', 'Ghi90', 'GhiMoy'
]
target_col = 'PV_Total'

# Reconvertir 'Date' en datetime après le resample
df_prev_numeric['Date'] = pd.to_datetime(df_prev_numeric['Date'], errors='coerce')
df_hist_numeric['Date'] = pd.to_datetime(df_hist_numeric['Date'], errors='coerce')

df_prev_numeric = df_prev_numeric.set_index('Date')
df_hist_numeric = df_hist_numeric.set_index('Date')

# Ajout de features temporelles
df_prev_numeric['Hour'] = df_prev_numeric.index.hour
df_prev_numeric['Day'] = df_prev_numeric.index.dayofyear

# Lags de production PV
df_prev_numeric['Lag_1'] = df_hist_numeric['PV_Total'].shift(1)
df_prev_numeric['Lag_2'] = df_hist_numeric['PV_Total'].shift(2)

# Liste finale de features
features = ['GhiMoy', 'DniMoy', 'Ghi90', 'Dni90', 'Hour', 'Day', 'Lag_1', 'Lag_2']

# Fusion => DataFrame complet (features + target)
data = pd.concat([df_prev_numeric[features], df_hist_numeric[[target_col]]], axis=1).dropna()

# --------------------------------------------------------------------------------
# 5) NORMALISATION
# --------------------------------------------------------------------------------
data = data.sort_index()  # s'assurer de l'ordre par date
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(data)

N = len(data)
num_features = len(features)  # + 1 colonne target => total = num_features + 1
data_index = data.index       # DatetimeIndex (tz-naive)

# --------------------------------------------------------------------------------
# 6) CRÉATION DES SEQUENCES (FENÊTRES DE 24H)
# --------------------------------------------------------------------------------
sequence_length = 24
target_index = num_features  # la cible (PV_Total) est la dernière colonne

def create_sequences(array_data, array_index, seq_length=24, target_idx=0):
    """
    array_data : scaled_data (numpy) [N, nb_col]
    array_index: data_index (DatetimeIndex) de taille N
    seq_length : fenêtre (24 heures)
    target_idx : index de la colonne cible
    Retourne une liste de tuples (X_seq, y_seq, date_cible) EN ORDRE CHRONOLOGIQUE
    """
    sequences = []
    for i in range(len(array_data) - seq_length):
        X_seq = array_data[i : i+seq_length, :-1]       # toutes les colonnes sauf la cible
        y_seq = array_data[i + seq_length, target_idx]  # la valeur cible
        date_cible = array_index[i + seq_length]        # la date associée à la cible
        sequences.append((X_seq, y_seq, date_cible))
    return sequences

all_sequences = create_sequences(
    array_data=scaled_data,
    array_index=data_index,
    seq_length=sequence_length,
    target_idx=target_index
)
# all_sequences est déjà en ORDRE CHRONOLOGIQUE (du plus ancien au plus récent)

# --------------------------------------------------------------------------------
# 7) SPLIT TEMPOREL (SANS DESORDRE)
#    Par exemple, jeu de test = [2024-06-01, 2024-09-12]
# --------------------------------------------------------------------------------
date_start_test = pd.Timestamp('2024-06-01')
date_end_test   = pd.Timestamp('2024-09-12')

train_list = []
test_list = []

for (X_seq, y_seq, date_cible) in all_sequences:
    # On place la séquence dans test si la date_cible est dans [date_start_test, date_end_test]
    if date_start_test <= date_cible <= date_end_test:
        test_list.append((X_seq, y_seq, date_cible))
    else:
        train_list.append((X_seq, y_seq, date_cible))

# Convertir en np.array
X_train = np.array([item[0] for item in train_list])
y_train = np.array([item[1] for item in train_list])
X_test  = np.array([item[0] for item in test_list])
y_test  = np.array([item[1] for item in test_list])
dates_test = np.array([item[2] for item in test_list], dtype='datetime64[ns]')

# Le train et le test sont **ordonnés chronologiquement** (même ordre que all_sequences)
print("Train size:", len(X_train), "séquences")
print("Test size :", len(X_test), "séquences (de", date_start_test.date(), "à", date_end_test.date(), ")")

# --------------------------------------------------------------------------------
# 8) CONSTRUCTION DU MODELE LSTM
# --------------------------------------------------------------------------------
model = Sequential([
    Bidirectional(LSTM(256, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2]))),
    Dropout(0.2),
    Bidirectional(LSTM(128, return_sequences=True)),
    Dropout(0.2),
    LSTM(64),
    Dropout(0.2),
    Dense(64, activation='relu'),
    Dense(32, activation='relu'),
    Dense(1)
])


optimizer = Adam(learning_rate=0.001)
model.compile(optimizer=optimizer, loss='mse', metrics=['mae'])

# --------------------------------------------------------------------------------
# 9) LEARNING RATE SCHEDULER (FACULTATIF)
# --------------------------------------------------------------------------------
def lr_schedule(epoch, lr):
    if epoch > 10:
        return lr * 0.9
    return lr

lr_scheduler = LearningRateScheduler(lr_schedule, verbose=1)

# --------------------------------------------------------------------------------
# 10) ENTRAINEMENT (SANS SHUFFLE)
# --------------------------------------------------------------------------------
# shuffle=False => on conserve l'ordre des séquences pendant l'entraînement
# validation_split=0.2 => les 20% DERNIERS échantillons du train (en ordre) serviront de validation
history = model.fit(
    X_train, y_train,
    epochs=30,
    batch_size=32,
    validation_split=0.2,
    callbacks=[lr_scheduler],
    verbose=1,
    shuffle=False
)

# --------------------------------------------------------------------------------
# 11) PREDICTION ET INVERSION DU SCALING
# --------------------------------------------------------------------------------
y_pred = model.predict(X_test)

# On reconstruit la matrice (0 pour features, y_* en dernière colonne)
y_test_rescaled = scaler.inverse_transform(
    np.c_[np.zeros((len(y_test), num_features)), y_test]
)[:, -1]
y_pred_rescaled = scaler.inverse_transform(
    np.c_[np.zeros((len(y_pred), num_features)), y_pred]
)[:, -1]

# --------------------------------------------------------------------------------
# 12) EVALUATION
# --------------------------------------------------------------------------------
mae  = mean_absolute_error(y_test_rescaled, y_pred_rescaled)
rmse = np.sqrt(mean_squared_error(y_test_rescaled, y_pred_rescaled))
r2   = r2_score(y_test_rescaled, y_pred_rescaled)

print(f"MAE:  {mae:.2f}")
print(f"RMSE: {rmse:.2f}")
print(f"R2:   {r2:.2f}")

# --------------------------------------------------------------------------------
# 13) CRÉATION DU CSV RÉSULTATS (ORDONNÉ)
# --------------------------------------------------------------------------------
results_df = pd.DataFrame({
    'Date': dates_test,          
    'True_PV': y_test_rescaled,  
    'Pred_PV': y_pred_rescaled
})

# Pour être sûr que c'est ordonné (il devrait déjà l'être), on trie par date
results_df = results_df.sort_values(by='Date')

results_df.to_csv('test_vs_pred_timewindow.csv', index=False)
print("Fichier CSV 'test_vs_pred_timewindow.csv' enregistré avec succès !")

# --------------------------------------------------------------------------------
# 14) VISUALISATION
# --------------------------------------------------------------------------------

# A) Courbes de Loss
plt.figure(figsize=(10, 6))
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.title('Training & Validation Loss (Ordre Chronologique)')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.show()

# B) Comparaison Valeurs Réelles vs Prédictions sur Test
plt.figure(figsize=(10, 6))
plt.plot(y_test_rescaled[:100], label='Actual', marker='o')
plt.plot(y_pred_rescaled[:100], label='Predicted', marker='x')
plt.title('Predicted vs Actual PV (Test set, first 100 samples)')
plt.xlabel('Time Steps in Test Set')
plt.ylabel('PV Production')
plt.legend()
plt.show()

# C) Distribution des erreurs
errors = y_test_rescaled - y_pred_rescaled
plt.figure(figsize=(10, 6))
plt.hist(errors, bins=30, color='blue', alpha=0.7)
plt.title('Error Distribution')
plt.xlabel('Prediction Error')
plt.ylabel('Frequency')
plt.show()
