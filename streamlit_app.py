import numpy as np
import pandas as pd
import requests
import json

import streamlit as st

@st.cache_resource
def load_data():
    # load dataframes with data
    pass

# data_seasons, data_all = load_data()

st.title("Информация о текущей температуре в городе")

city = st.selectbox("Выберите город", ["Beijing", "Berlin", "Cairo", "Dubai", "London", "Los Angeles", "Mexico City", "Moscow", "Mumbai", "New York", "Paris", "Rio de Janeiro", "Singapore", "Sydney", "Tokyo"])

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

if st.button("Узнать температуру"):
    if not st.session_state.key_valid:
        st.error("Введите корректный API ключ")
    elif not city:
        st.error("Выберите город")
    else:
        r = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={city}&APPID={api_key}"
            )
        temp = json.loads(r.text)['main']['temp'] - 273.15
        st.metric(label="Текущая температура:", value=f"{temp} °C")