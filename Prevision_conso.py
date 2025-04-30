import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Charger les données
file_path = 'conso_historiques_clean.csv'
df_conso = pd.read_csv(
    file_path, 
    delimiter=';', 
    dtype=str,  
    low_memory=False
)

# Nettoyage des colonnes
df_conso.columns = df_conso.columns.str.strip()

# Liste des colonnes de puissance à prédire
target_cols = ['Ptot_HA', 'Ptot_HEI', 'Ptot_HEI_13RT', 'Ptot_HEI_5RNS', 'Ptot_RIZOMM']

# Supprimer les lignes où Ptot_HEI est null
df_conso = df_conso[df_conso['Ptot_HEI'].astype(str).str.strip().replace(['null', '', 'None'], np.nan).notna()]

# Remplacer 'null', '', 'None' par '0' et convertir en float pour les colonnes cibles
for col in target_cols:
    df_conso[col] = (
        df_conso[col]
        .astype(str)
        .str.strip()
        .replace(['null', '', 'None'], '0')
        .str.replace(',', '.')
        .astype(float)
    )

# Convertir la colonne Date
df_conso['Date'] = pd.to_datetime(df_conso['Date'], errors='coerce', utc=True)
df_conso = df_conso.dropna(subset=['Date'])  # Supprimer les lignes sans date

# Ajouter les caractéristiques temporelles
df_conso['hour'] = df_conso['Date'].dt.hour
df_conso['day_of_week'] = df_conso['Date'].dt.dayofweek
df_conso['month'] = df_conso['Date'].dt.month

# Sélection des colonnes d'entrée
all_features = target_cols + ['hour', 'day_of_week', 'month']
df = df_conso[all_features]

# Normalisation des données (indépendante pour chaque colonne)
scalers = {}
scaled_data = df.copy()
for col in target_cols:
    scalers[col] = MinMaxScaler()
    scaled_data[col] = scalers[col].fit_transform(df[[col]])

scaled_data = scaled_data.values  # Convertir en array numpy

# Fonction pour créer des séquences temporelles
def create_sequences(data, seq_length, num_targets):
    X, y = [], []
    for i in range(len(data) - seq_length):
        X.append(data[i:i+seq_length])
        y.append(data[i+seq_length, :num_targets]) 
    return np.array(X), np.array(y)

SEQ_LENGTH = 24  # 24 heures d'historique pour prédire l'heure suivante
X, y = create_sequences(scaled_data, SEQ_LENGTH, len(target_cols))
train_size = int(0.8 * len(X))
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Construire le modèle LSTM multi-sortie
model = Sequential([
    LSTM(64, activation='relu', input_shape=(SEQ_LENGTH, len(all_features)), return_sequences=True),
    Dropout(0.2),
    LSTM(32, activation='relu'),
    Dense(len(target_cols))  
])

model.compile(optimizer='adam', loss='mse')

# Entraînement du modèle
history = model.fit(
    X_train, y_train,
    epochs=20, 
    batch_size=64,
    validation_data=(X_test, y_test),
    verbose=1
)

# Prédictions
y_pred = model.predict(X_test)

# Inverse scaling des prédictions et des valeurs réelles pour chaque colonne séparément
y_pred_actual = np.zeros_like(y_pred)
y_test_actual = np.zeros_like(y_test)

for i, col in enumerate(target_cols):
    y_pred_actual[:, i] = scalers[col].inverse_transform(y_pred[:, i].reshape(-1, 1)).flatten()
    y_test_actual[:, i] = scalers[col].inverse_transform(y_test[:, i].reshape(-1, 1)).flatten()

# Affichage des résultats pour chaque colonne séparément
for i, target in enumerate(target_cols):
    plt.figure(figsize=(10, 5))
    plt.plot(y_test_actual[:, i], label=f'True {target}', color='blue')
    plt.plot(y_pred_actual[:, i], label=f'Predicted {target}', color='red', alpha=0.7)
    plt.title(f'Power Consumption Prediction for {target}')
    plt.xlabel('Time Steps')
    plt.ylabel('Power')
    plt.legend()
    plt.show()




# ---------------------------
# 1) Retrouver la colonne Date pour chaque échantillon de test
# ---------------------------

# Longueur totale après nettoyage
N = len(df_conso)  
test_start_index = train_size + SEQ_LENGTH  
test_end_index = N  

test_indices = range(test_start_index, test_end_index)
dates_test = df_conso['Date'].iloc[test_indices].values

# ---------------------------
# 2) Construire le DataFrame de résultats
# ---------------------------
# On veut avoir pour chaque ligne : Date, + colonnes "réelles" vs "prédites"

results_dict = {
    'Date': dates_test
}

for i, col in enumerate(target_cols):
    results_dict[f'True_{col}'] = y_test_actual[:, i]
    results_dict[f'Pred_{col}'] = y_pred_actual[:, i]

df_results = pd.DataFrame(results_dict)

df_results.to_csv('test_vs_real.csv', index=False)

print("Fichier CSV 'test_vs_real.csv' enregistré avec succès !")
