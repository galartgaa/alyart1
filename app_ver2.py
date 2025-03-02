import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

#streamlit run app_ver3.py - -client.showSidebarNavigation = False
# Функция для расчета доходности портфеля
def calculate_portfolio_returns(all_data, ticker_columns_insert, weights_insert):
    if len(ticker_columns_insert) != len(weights_insert):
        raise ValueError("Количество тикеров и весов должно совпадать.")

    filtered_data = all_data[all_data['ticker'].isin(ticker_columns_insert)].copy()
    filtered_data['Daily Change'] = filtered_data.groupby('ticker')['Close'].pct_change()
    weights_dict = dict(zip(ticker_columns_insert, weights_insert))
    filtered_data['Weight'] = filtered_data['ticker'].map(weights_dict)
    filtered_data['Weighted Change'] = filtered_data['Daily Change'] * filtered_data['Weight']
    filtered_data['Date'] = pd.to_datetime(filtered_data['Date'])
    filtered_data['Date'] = filtered_data['Date'].dt.date

    portfolio_returns = (
        filtered_data.groupby('Date')['Weighted Change']
        .sum()
        .reset_index()
        .rename(columns={'Weighted Change': 'Portfolio Daily Return'})
    )

    portfolio_returns['Cumulative Return'] = (1 + portfolio_returns['Portfolio Daily Return']).cumprod()
    return portfolio_returns

# Функция для расчета метрик портфеля
def calculate_portfolio_metrics_with_rolling_drawdown(portfolio_df):
    portfolio_df = portfolio_df.sort_values('Date').copy()
    var_95 = np.percentile(portfolio_df['Portfolio Daily Return'], 5)
    portfolio_df['Cumulative Return'] = (1 + portfolio_df['Portfolio Daily Return']).cumprod()
    portfolio_df['Date'] = pd.to_datetime(portfolio_df['Date'])
    today = portfolio_df['Date'].max()
    date_1y = today - pd.DateOffset(years=1)
    date_2y = today - pd.DateOffset(years=2)
    date_3y = today - pd.DateOffset(years=3)

    df_1y = portfolio_df[portfolio_df['Date'] >= date_1y]
    df_2y = portfolio_df[portfolio_df['Date'] >= date_2y]
    df_3y = portfolio_df[portfolio_df['Date'] >= date_3y]

    pnl_1_year = df_1y['Cumulative Return'].iloc[-1] / df_1y['Cumulative Return'].iloc[0] - 1
    pnl_2_year = df_2y['Cumulative Return'].iloc[-1] / df_2y['Cumulative Return'].iloc[0] - 1
    pnl_3_year = df_3y['Cumulative Return'].iloc[-1] / df_3y['Cumulative Return'].iloc[0] - 1

    portfolio_df['Rolling Max 255'] = portfolio_df['Cumulative Return'].rolling(window=255, min_periods=1).max()
    portfolio_df['Drawdown 255'] = portfolio_df['Cumulative Return'] / portfolio_df['Rolling Max 255'] - 1
    max_drawdown_255 = portfolio_df['Drawdown 255'].min()

    return {
        'VaR_95': var_95,
        'PnL_1_Year': pnl_1_year,
        'PnL_2_Year': pnl_2_year,
        'PnL_3_Year': pnl_3_year,
        'Max_Drawdown_255': max_drawdown_255
    }

# Настройки страницы
st.set_page_config(layout="wide")

# Загружаем данные
df = pd.read_csv('crypto_data.csv')

# Создаем вкладки
tabs = st.tabs(["Custom Portfolio", "Ready Strategies"])
ecosystems = ['bitcoin', 'ethereum', 'ripple', 'solana', 'binance', 'dogecoin',
              'cardano', 'tron', 'stellar', 'internet-computer', 'monero',
              'filecoin', 'cosmos']
categories = ['store-of-value', 'smart-contracts', 'payments', 'stablecoin',
              'platform', 'exchange', 'meme', 'defi', 'privacy', 'storage',
              'interoperability']
# Первая вкладка: пользовательский портфель
with tabs[0]:
    st.header("Custom Portfolio")

    # Фильтры
    st.subheader("Filters")

    # Фильтры в две колонки
    col1, col2 = st.columns(2)

    with col1:
        initial_value = st.number_input("Initial Investment Amount", min_value=0.0, value=1000.0, step=10.0)

        # Выбор категорий
        selected_categories = st.multiselect("Select Categories", categories, default=categories)

        # Выбор экосистем
        selected_ecosystems = st.multiselect("Select Ecosystems", ecosystems, default=ecosystems)

    with col2:
        # Фильтрация тикеров по выбранным категориям и экосистемам
        filtered_tickers = df[
            (df['category'].isin(selected_categories)) &
            (df['ecosystem'].isin(selected_ecosystems))
            ]['ticker'].unique().tolist()

        # Выбор тикеров
        selected_tickers = st.multiselect("Select Tickers", filtered_tickers, default=filtered_tickers)



    with st.expander("Set Weights for Selected Tickers"):
        weights = [
            st.number_input(f"Weight for {ticker}", min_value=0.0, max_value=1.0, value=1.0 / len(selected_tickers))
            for ticker in selected_tickers
        ]
    # Фильтрация данных
    filtered_df = df[df['ticker'].isin(selected_tickers)]
    filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
    filtered_df = filtered_df[filtered_df['ecosystem'].isin(selected_ecosystems)]

    # Рассчитываем доходность портфеля
    portfolio_returns = calculate_portfolio_returns(filtered_df, selected_tickers, weights)
    portfolio_metrics = calculate_portfolio_metrics_with_rolling_drawdown(portfolio_returns)

    # График
    fig = px.line(portfolio_returns, x='Date', y='Cumulative Return', title="Portfolio Cumulative Growth")
    fig.update_xaxes(tickangle=0, title="Date")
    fig.update_yaxes(title="Cumulative Return")

    # Отображаем график
    st.plotly_chart(fig, use_container_width=True)

    # Отображение метрик
    col1, col2 = st.columns(2)
    col2.metric("VaR 95%", f"{portfolio_metrics['VaR_95']:.2f}")
    col1.metric("PnL (1 Year)", f"{portfolio_metrics['PnL_1_Year']:.2%}")
    col1.metric("PnL (3 Years)", f"{portfolio_metrics['PnL_3_Year']:.2%}")
    col2.metric("Max Drawdown (255 Days)", f"{portfolio_metrics['Max_Drawdown_255']:.2%}")

    # Кнопка
    st.markdown(
        """
        <style>
        .big-green-button {
            background-color: #28a745; 
            color: white;
            font-size: 20px;
            padding: 20px 40px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown('<button class="big-green-button">Купить портфель</button>', unsafe_allow_html=True)

# Вторая вкладка: Готовые стратегии
with tabs[1]:
    st.header("Ready Strategies")

    st.subheader("Strategy 1: Top 1000 Coins")
    st.write("Широкий спред токенов, купленные пропорционально их ликвидности")

    st.subheader("Strategy 2: MobyDik")
    st.write("Стратегия, следующая сигналам китовых кошельков")

    st.subheader("Strategy 3: 150 Tech Indicators")
    st.write("Роботизированная стратегия, основанная на популярных тех индикаторах")

    st.subheader("Strategy 4: ChatGPT")
    st.write("Top-100 ликвидных компаний, разрабатывающих LLM-модели")

    # Кнопка
    st.markdown(
        """
        <style>
        .big-green-button {
            background-color: #28a745; 
            color: white;
            font-size: 20px;
            padding: 20px 40px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }
        </style>
        """, unsafe_allow_html=True
    )

    st.markdown('<button class="big-green-button">Купить портфель</button>', unsafe_allow_html=True)