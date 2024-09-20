import streamlit as st, pandas as pd, numpy as np, yfinance as yf
import streamlit.components.v1 as components
from pandas.tseries.holiday import USFederalHolidayCalendar
from scipy.stats import norm, chi2
import datetime as dt
import requests
import math

#------ Calculate Trading Days Between Dates ------#
def days_to_expiration(start_date, expiration_date):
    us_bd = pd.offsets.CustomBusinessDay(calendar=USFederalHolidayCalendar())
    business_days = pd.date_range(start=start_date, end=expiration_date, freq=us_bd)
    df = pd.DataFrame(business_days, columns=["Business Days"])
    days_left = df.shape[0]
    return df, days_left

#------ Append Volatility ------#
def historical_vol(df, vol_days):
    df["daily return"] = df["close price"].pct_change()
    df["historical volatility"] = df["daily return"].rolling(window=vol_days).std() * np.sqrt(252)
    df = df.dropna(subset=["historical volatility"])
    return df

#------ Black-Scholes Functions ------#
def theoretical_call_price(spot, strike, rate, time, volatility):
    d1 = (np.log(spot/strike) + (rate + (volatility**2)/2)*time)/(volatility*np.sqrt(time))
    d2 = (np.log(spot/strike) + (rate - (volatility**2)/2)*time)/(volatility*np.sqrt(time)) 
    call_price = spot * norm.cdf(d1) - (strike *  np.exp(-rate * time) * norm.cdf(d2))
    return call_price

def theoretical_put_price(spot, strike, rate, time, volatility):
    d1 = (np.log(spot/strike) + (rate + (volatility**2)/2)*time)/(volatility*np.sqrt(time))
    d2 = (np.log(spot/strike) + (rate - (volatility**2)/2)*time)/(volatility*np.sqrt(time)) 
    put_price =  strike * np.exp(-rate * time) * norm.cdf(-d2) - (spot * norm.cdf(-d1))
    return put_price

#------ Retrieve Historical Interest Rates ------#
def get_treasury_yield(start, expiry_day, expiry_month, expiry_year):
    expiry_day = int(expiry_day) + 1
    expiry_day = str(expiry_day).zfill(2)
    end = f"20{expiry_year}-{expiry_month}-{expiry_day}"
    ticker = "^IRX"
    df = yf.download(ticker, start=start, end=end)
    df.reset_index(inplace=True)
    df["date"] = df["Date"]
    df["rate"] = df["Close"]
    df = df[["date","rate"]]
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df

#------ Retrieve Historical Options Close Prices ------#
def get_options_hist(ticker, strike, start, expiry_day, expiry_month, expiry_year, cop):
    # Check determine if we are retrieving calls or puts
    if cop == "C":
        contract = "call"
    elif cop == "P":
        contract = "put"
    else:
        print("Please enter 'C' or 'P' for cop variable" )
        return None

    # Format url
    num = str(math.floor(strike)).zfill(5)
    dec = "{:.2f}".format(strike % 1)
    tickerPrice = f"{num}{dec[2:]}"
    optionTicker = f"{ticker}{expiry_year}{expiry_month}{expiry_day}{cop}{tickerPrice}0"
    end = f"20{expiry_year}-{expiry_month}-{expiry_day}"
    url = f"https://api.polygon.io/v2/aggs/ticker/O:{optionTicker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&apiKey=geIbpipoZeaC7IN7wBdiIKpwH8LuBiyH"
    
    # Make a request to the API
    try:
        response = requests.get(url = url)

        if response.status_code == 429:
            print(f"Error {response.status_code}")
            print(f"url: {url}")
            print(f"Response: {response.text}")
            return response.status_code
        r = response.json()

    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return None
    except requests.exceptions.InvalidURL as e:
        print(f"Invalid URL: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    # Convert to datetime
    expiration_date = dt.datetime.strptime(end, "%Y-%m-%d")
    
    # Build the table
    data = []
    for result in r["results"]:
        # Convert timestamp to date
        date = dt.datetime.fromtimestamp(result["t"] / 1000)

        # Calculate days to expiration 
        days_left = days_to_expiration(date, expiration_date)[1]

        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "days to expiration": days_left,
            f"{contract} price": float(result["c"])
            })
    
    df = pd.DataFrame(data)
    return df

#------ Retrieve Historical Underlying Close Prices ------#
def get_stock_hist(ticker, start, end_day, end_month, end_year):
    
    # Format url
    end = f"20{end_year}-{end_month}-{end_day}"
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}?adjusted=true&sort=asc&apiKey=geIbpipoZeaC7IN7wBdiIKpwH8LuBiyH"
    try:
        # Make a request to the API
        response = requests.get(url = url)
        if response.status_code == 429:
            print(f"Error {response.status_code}")
            print(f"url: {url}")
            print(f"Response: {response.text}")
            return response.status_code
        r = response.json()
        
    
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        return None
    except requests.exceptions.InvalidURL as e:
        print(f"Invalid URL: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

    # Build the table
    data = []
    for result in r["results"]:
        # Convert timestamp to date
        date = dt.datetime.fromtimestamp(result["t"] / 1000)
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "close price": float(result["c"])
            })
    df1 = pd.DataFrame(data)

    # Filter out non-trading days
    df2 = days_to_expiration(start, end)[0]
    df2.rename(columns={"Business Days": "date"}, inplace=True)
    df2["date"] = df2["date"].dt.strftime("%Y-%m-%d")
    df = pd.merge(df2, df1, on = "date")#, how = "left")
    return df 

#------ Construct Dataframe ------#
def get_prices_merge(ticker, strike, start, expiry_day, expiry_month, expiry_year, vol_days):
    
    # Get data frames
    dfcalls = get_options_hist(ticker=ticker, strike=strike, start=start, expiry_day=expiry_day, expiry_month=expiry_month, expiry_year=expiry_year, cop = "C")
    dfputs = get_options_hist(ticker=ticker, strike=strike, start=start, expiry_day=expiry_day, expiry_month=expiry_month, expiry_year=expiry_year, cop = "P")
    rates = get_treasury_yield(start=start, expiry_day=expiry_day, expiry_month=expiry_month, expiry_year=expiry_year)

    # Get 365 days extra underlying data
    pre_start = dt.datetime.strptime(start, "%Y-%m-%d") - dt.timedelta(days=365)
    pre_start = pre_start.strftime("%Y-%m-%d")
    df_underlying = get_stock_hist(ticker=ticker, start=pre_start, end_day = expiry_day , end_month = expiry_month, end_year = expiry_year)
    df_underlying = historical_vol(df_underlying, vol_days=vol_days)

    # Stop if API requests returned an error
    if isinstance(dfcalls, int) or dfcalls is None:
        return dfcalls
    if isinstance(dfputs, int) or dfputs is None:
        return dfputs
    if isinstance(df_underlying, int) or df_underlying is None:
        return df_underlying

    # Merge data frames
    options_df = pd.merge(dfcalls, dfputs[["date","put price"]], on = "date", how = "left")
    prices_df = pd.merge(options_df, df_underlying, on = "date", how = "left")
    rates_df = pd.merge(prices_df, rates, on="date", how = "left")
    return rates_df

#------ Add Theoretical Prices ------#
def append_theoretical(df, strike):
    df["expiration for bs"] = df["days to expiration"]/365
    df["t call price"] = theoretical_call_price(df["close price"], strike, df["rate"]/100, df["expiration for bs"], df["historical volatility"])
    df["t put price"] = theoretical_put_price(df["close price"], strike, df["rate"]/100, df["expiration for bs"], df["historical volatility"])
    return df


#------ Chi-Square Goodness Of Fit Test ------#
def chi_square(df, sig_level):
    df = df.iloc[:-1]
    df["chi square calls"] = ((df["t call price"]-df["call price"])**2)/df["t call price"]
    df["chi square puts"] = ((df["t put price"]-df["put price"])**2)/df["t put price"]
    df.loc[df["t call price"] < 0.01, "chi square calls"] = np.nan
    df.loc[df["t put price"] < 0.01, "chi square puts"] = np.nan

    calls_dof = df["chi square calls"].count()
    puts_dof = df["chi square puts"].count()
    gof_calls = float(df["chi square calls"].sum())
    gof_puts = float(df["chi square puts"].sum())
    chi_square_critical_calls = chi2.ppf(sig_level, calls_dof)
    chi_square_critical_puts = chi2.ppf(sig_level, puts_dof)

    if gof_calls < chi_square_critical_calls:
        call_result = "PASS"
    else:
        call_result = "FAIL"

    if gof_puts < chi_square_critical_puts:
        put_result = "PASS"
    else:
        put_result = "FAIL"

    return gof_calls, gof_puts, chi_square_critical_calls, chi_square_critical_puts, call_result, put_result, df

#------ Format Table ------#
def format_df(df):
    # Rearrange and cut columns
    final_columns = ["date", "days to expiration", "close price", "call price", "t call price", "put price", "t put price", "historical volatility", "rate"]
    final_labels = ["Date", "Days to Expiration", "Stock Price", "Call Price", "Theoretical Call Price", "Put Price", "Theoretical Put Price", "Historical Volatility", "Interest Rate"]
    
    final_df = df[final_columns]
    final_df.columns = final_labels

    return final_df


#------ Streamlit Interface ------#
st.set_page_config(page_title="Historical Options Pricing", page_icon=":bank:")

if "data" not in st.session_state:
    st.session_state.data = None
if "formatted_df" not in st.session_state:
    st.session_state.formatted_df = None

st.subheader("Historical Options Pricer Using Black-Scholes Model")
st.write("Enter your parameters in the sidebar to create a table of historical options and stock data")

# Construct Side Bar
st.sidebar.button("Thomas Gray - LinkedIn", "www.linkedin.com/in/thomas-gray-4223a728b", "Follow me on LinkedIn", 20)

st.sidebar.header("Parameters")
ticker_input = st.sidebar.text_input("Ticker", value = "AAPL")
strike_input = st.sidebar.number_input("Strike Price", value = float(220), min_value=0.5, step = 0.5)
exDate_input = st.sidebar.date_input("Expiration Date",
                            value = dt.date(2024, 8, 30),
                            min_value = dt.date(2020, 1, 1)#,
                            #max_value = dt.datetime.today()
                            )

#------ Create standard startdate ------#
delta = dt.timedelta(days = 30)
basic_start = exDate_input - delta
start_input = st.sidebar.date_input("Start Date", 
                                    value = basic_start,
                                    min_value = dt.date(2020, 1, 1),
                                    max_value = dt.datetime.today() 
                                    )

#risk_free_rate  = st.sidebar.number_input("Risk-Free Interest Rate", value = 3.85, min_value=float(0), step=0.01)
vol_days = st.sidebar.slider("No. of Days Used to Calculate Historical Volatility", min_value=1, max_value=250, value=21)

exDay_input = exDate_input.strftime("%d") 
exMonth_input = exDate_input.strftime("%m")
exYear_input = exDate_input.strftime("%y")


#------ Sidebar and Table Generation ------#
if st.sidebar.button("Generate Table"):
    with st.spinner("Generating table..."):
        df = get_prices_merge(ticker_input, strike_input, start_input.strftime("%Y-%m-%d"), exDay_input, exMonth_input, exYear_input, vol_days=vol_days)
        if isinstance(df, int):
            st.error(f"Error {df}")
            if df == 429:
                st.error("You can only attempt to generate a table twice in one minute")
        if df is None:
            st.error("Couldn't retrieve data, please check inputs")
        else:
            df = append_theoretical(df, strike_input)#, risk_free_rate)
            formatted_df = format_df(df)
            st.session_state.data = df
            st.session_state.formatted_df = formatted_df
            st.line_chart(st.session_state.formatted_df, x="Date", y=["Call Price", "Theoretical Call Price"], color=["#27ae60","#3498db"])
            st.line_chart(st.session_state.formatted_df, x="Date", y=["Put Price", "Theoretical Put Price"], color=["#27ae60","#3498db"])
            price_cols = ["Stock Price", "Call Price", "Theoretical Call Price", "Put Price", "Theoretical Put Price"]
            st.session_state.formatted_df[price_cols] = st.session_state.formatted_df[price_cols].applymap("${:,.2f}".format)
            st.write(st.session_state.formatted_df)
        
st.divider()

#------ Goodness of Fit Test ------#
if st.session_state.data is not None:
    st.subheader("Chi-Square Goodness-of-Fit Test")
    sig_level = st.number_input("Significance Level %", value=float(1), step=0.01)
    gof = chi_square(st.session_state.data, sig_level/100)
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Calls test statistic: {round(gof[0],2)}")        
        st.write(f"Calls critical value: {round(gof[2],2)}")
        st.write(f"Call Values: {gof[4]}")
    with col2:
        st.write(f"Puts test statistic: {round(gof[1],2)}")
        st.write(f"Puts critical value: {round(gof[3],2)}")
        st.write(f"Put Values: {gof[5]}")
    #st.write(gof[6])
else:
    st.warning("Waiting for data")

st.write(f"If you have any questions or suggestions please contact me via LinkedIn)
