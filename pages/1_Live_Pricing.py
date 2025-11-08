import streamlit as st, pandas as pd, datetime as dt
from pandas.tseries.holiday import USFederalHolidayCalendar
import requests
from bs4 import BeautifulSoup
import statistics as stats
from scipy.stats import norm
import numpy as np
import math
import time 

def get_price(ticker, exchange):
    response = requests.get(f'https://www.google.com/finance/quote/{ticker}:{exchange}?hl=en')
    soup = BeautifulSoup(response.text, 'html.parser')
    class1 = "YMlKec fxKbKc"
    return float(soup.find(class_=class1).text.strip()[1:].replace(",",""))

def days_to_expiration(start_date, expiration_date):
    us_bd = pd.offsets.CustomBusinessDay(calendar=USFederalHolidayCalendar())
    business_days = pd.date_range(start=start_date, end=expiration_date, freq=us_bd)
    df = pd.DataFrame(business_days, columns=['Business Days'])
    days_left = df.shape[0]
    return df, days_left

def theoretical_call_price(spot, strike, rate, time, volatility):
    d1 = (np.log(spot/strike) + (rate + (volatility**2)/2)*time)/(volatility*math.sqrt(time))
    d2 = (np.log(spot/strike) + (rate - (volatility**2)/2)*time)/(volatility*math.sqrt(time)) 
    call_price = round(spot * stats.NormalDist().cdf(x = d1) - (strike *  math.exp(-rate * time) * stats.NormalDist().cdf(x = d2)), 2)
    call_price = '{0:.2f}'.format(call_price)
    return f'${call_price}'

def theoretical_put_price(spot, strike, rate, time, volatility):
    d1 = (np.log(spot/strike) + (rate + (volatility**2)/2)*time)/(volatility*math.sqrt(time))
    d2 = (np.log(spot/strike) + (rate - (volatility**2)/2)*time)/(volatility*math.sqrt(time)) 
    put_price =  strike * math.exp(-rate * time) * stats.NormalDist().cdf(-d2) - (spot * stats.NormalDist().cdf(-d1))
    put_price = '{0:.2f}'.format(put_price)
    return f'${put_price}'

st.set_page_config(page_title="Live Options Pricing", page_icon=":cash:")

st.header('Live Black-Scholes Option Pricer')
ticker = st.sidebar.text_input("Ticker", "SOFI")
exchange = st.sidebar.text_input("Exchange", "NASDAQ")
real_time_price = get_price(ticker = ticker, exchange = exchange)

strike_list = [x/2 for x in range(5, 21)] + [x for x in range(22,300)]
strike_price = st.sidebar.multiselect("Strike Prices", strike_list)

if strike_price:

    expiration = st.sidebar.date_input("Expiration Date", value=dt.datetime.today())
    days = days_to_expiration(dt.datetime.today(), expiration)
    days = days[1]
    
    rate = st.sidebar.number_input("Risk-Free Interest Rate", value = 3.75, min_value=float(0), step=0.01)
    volatility = st.sidebar.number_input("Volatility %", value=float(75), min_value=float(0), step=0.01)
    
    
    df = []
    for price in strike_price:
        df.append({"Strike": price,
                   "T Call Price": theoretical_call_price(spot = real_time_price, strike = price, time = days/365, rate = rate/100, volatility = volatility/100),
                   "T Put Price": theoretical_put_price(spot = real_time_price, strike = price, time = days/365, rate = rate/100, volatility = volatility/100)}
        )
    df = pd.DataFrame(df)
    
    st.write(f"Real Time Price = ${real_time_price}")
    st.write(df.sort_values("Strike"))
    
    time.sleep(5)
    st.rerun()
else:
    st.warning("Choose strike prices of interest in the sidebar")
    st.stop()
