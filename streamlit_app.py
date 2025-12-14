import requests
import json

import streamlit as st
import numpy as np
import pandas as pd
import polars as pl
import matplotlib.pyplot as plt

from threading import RLock

_lock = RLock()

@st.cache_data
def load_data(uploaded_file):
    # если использовать пандас, получается в 4 раза медленнее (при наборе данных в 56к)
    # поэтому используем polars
    df_polars = pl.scan_csv(uploaded_file, try_parse_dates=True)
    result = (
        df_polars
        .sort(["city", "timestamp"])
        .with_columns(
            pl.col("temperature")
            .rolling_mean(window_size=30)
            .over("city")
            .alias("moving_avg_30d")
        )
        .with_columns(
            pl.mean("temperature").over(["city", "season"]).alias("mean_temp_season"),
            pl.std("temperature").over(["city", "season"]).alias("std_temp_season"),
        )
        .with_columns(
            (
                (pl.col("temperature") - pl.col("mean_temp_season")).abs()
                > 2 * pl.col("std_temp_season")
            ).alias("anomaly")
        )
    )
    return result.collect().to_pandas()

st.title("Информация о текущей температуре в городе")

uploaded_file = st.file_uploader("Загрузите CSV c историческими данными", type=["csv"])
df = load_data(uploaded_file)

if "key_valid" not in st.session_state:
    st.session_state.key_valid = False

api_key = st.text_input(
    "Введите api ключ OpenWeatherMap",
    type="password"
)

if st.button("Проверить API ключ"):
    try:
        r = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q=Moscow&APPID={api_key}"
        )
        st.session_state.key_valid = r.ok
    except Exception as e:
        st.session_state.key_valid = False
        st.error(str(e))

if st.session_state.key_valid:
    st.success("API ключ корректный")

city = st.selectbox("Выберите город", ["Beijing", "Berlin", "Cairo", "Dubai", "London", "Los Angeles", "Mexico City", "Moscow", "Mumbai", "New York", "Paris", "Rio de Janeiro", "Singapore", "Sydney", "Tokyo"])

df_city = df[df['city'] == city]

with _lock:
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.scatter(
        df_city['timestamp'],
        df_city['temperature'],
        color='orchid',
        s=15,
        label='Средняя температура за день'
    )
    ax.plot(
        df_city['timestamp'],
        df_city['moving_avg_30d'],
        color='darkviolet',
        linewidth=2,
        label='Скользящее среднее с окном в 30 дней'
    )
    anomalies = df_city[df_city['anomaly']]
    ax.scatter(
        anomalies['timestamp'],
        anomalies['temperature'],
        color='indigo',
        s=30,
        label='Аномальные дни',
        zorder=3
    )

    df_city['season_year'] = df_city['season'] + ' ' + df_city['timestamp'].dt.year.astype(str)

    season_ticks = (
        df_city.groupby('season_year')['timestamp']
        .min()
        .reset_index()
    )

    ax.set_xticks(season_ticks['timestamp'])
    ax.set_xticklabels(season_ticks['season_year'], rotation=45, ha='right')

    ax.set_title('Исторические данные по температуре')
    ax.set_xlabel('Время года')
    ax.set_ylabel('Температура')

    ax.legend()
    ax.grid(alpha=0.3)

    st.pyplot(fig)

if st.button("Узнать текущую температуру"):
    if not st.session_state.key_valid:
        st.error("Введите корректный API ключ")
    elif not city:
        st.error("Выберите город")
    else:
        # использование aiohttp ускоряет суммарное время запросов, если нужно сделать много запросов подряд
        # далее у нас синхронная часть, поэтому используем requests
        r = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={city}&APPID={api_key}"
            )
        temp = json.loads(r.text)['main']['temp'] - 273.15
        st.metric(label="Текущая температура:", value=f"{temp:.2f} °C")