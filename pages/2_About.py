import streamlit as st

st.set_page_config(page_title="About")

st.header('Historical Pricer')
st.markdown("""I made this app to explore the accuracy of the Black Scholes model, and to see how volatility affects options prices. The app takes inputs in the sidebar, then pulls historical data from Polygon and Yahoo Finance APIs. Once it has historical stock, options and treasury note data, it creates a historical options price for each date using the Black-Scholes model, and compares the theoretical prices to the real historical prices using graphs.
            
There is also a section that performs a Chi-Square Goodness-of-Fit test at a significance level chosen by the user. This is intended to quantify how well the model fits the real data. The test works by summing up the relative square-differences between the real prices and the modelled prices, and comparing this sum to a critical value that is determined by the amount of data points in the table, and the significance level chosen. The test deems the model not a good fit if the test statistic is larger than the critical value.""")
st.subheader("Historical Volatility")
st.markdown("The app uses historical volatility as an input in the Black-Scholes model. Historical Volatility is calculated by taking the standard deviation of the daily returns of the stock price over a given period. You can adjust the days used to calculate the historical volatility in the side bar, and see what amount of days makes the model fit best.")
st.subheader("Interest Rate")
st.markdown("The Black-Scholes Model requires you to input the “Risk-Free” interest rate, in this app I have used 13-Week US Treasury Bill yield to approximate the Risk-Free rate.")
st.subheader("Future Plans")
st.markdown("""Link the app to a SQL database that creates a table of inputs and a corresponding table of outputs that would include the most recent historical volatility calculation and whether the models passed the Goodness-of-Fit test

Create a graph of realised volatility vs implied volatility to study their relationship

Allow the user to choose between different historical volatility calculation methods such as the Parkinson Extreme Value Method and the Garman-Klass method

Allow the user to plot different greeks associated with the contract""")
st.header("Live Pricing")
st.markdown("""
This app takes the sidebar inputs and web scrapes a real-time stock price, then gives you real-time theoretical prices for different options contracts on the desired stock. My idea was to use a volatility value that is figured out using the historical price app,  and use it as an input in the real-time price app, allowing the user to spot trading opportunities by comparing with the corresponding real prices on an options chain.

This one is a work in progress and for the moment I would suggest trying it on a stock that is cheaper than $10 as I am yet to make it so the user can choose any strike price.
""")
st.header("Notes and Warnings")
st.markdown("""
The Chi-Square test is not perfect, sometimes one-off artifacts make the test fail when the model is actually a good fit
            
Due to limitations of the APIs used you may only attempt to generate a table twice in a single minute 
            
Inputs for "Ticker" and "Exchange" must be entered in all caps
""")