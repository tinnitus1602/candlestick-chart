import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import argparse

# Парсим аргументы командной строки
parser = argparse.ArgumentParser(description="Dynamic Bar Chart with Dash")
parser.add_argument('--file', type=str, required=True, help='Path to the CSV file')
parser.add_argument('--range1', type=int, default=720, help='Time range for the first bar in seconds')
parser.add_argument('--range2', type=int, default=1500, help='Time range for the second bar in seconds')
parser.add_argument('--range3', type=int, default=4000, help='Time range for the third bar in seconds')
args = parser.parse_args()

# Чтение данных из файла
data = pd.read_csv(args.file)

# Конвертируем 'T' в формат datetime
data['datetime'] = pd.to_datetime(data['T'], unit='ms')
data.set_index('datetime', inplace=True)

# Конвертируем 'p' (цена сделки) в числовой формат
data['p'] = pd.to_numeric(data['p'], errors='coerce')

# Создаем данные для графика с интервалом в 60 секунд
ohlc_data = data['p'].resample('60s').ohlc().dropna()

# Инициализируем Dash приложение
app = dash.Dash(__name__)

# Настройка макета Dash приложения
app.layout = html.Div([
    dcc.Graph(id='combined-chart', style={'width': '100%', 'height': '700px'}),
    html.Div([
        dcc.Graph(id='bar-chart', style={'width': '400px', 'height': '300px'})
    ], style={'position': 'absolute', 'top': '410px', 'left': '10px', 'border': '2px solid black', 'padding': '5px'}),
    dcc.Slider(
        id='time-slider',
        min=0,
        max=len(ohlc_data) - 1,
        value=len(ohlc_data) - 1,
        marks={i: str(ohlc_data.index[i]) for i in range(0, len(ohlc_data), max(1, len(ohlc_data)//10))},
        step=1,
        vertical=False
    )
])

@app.callback(
    [Output('combined-chart', 'figure'),
     Output('bar-chart', 'figure')],
    [Input('time-slider', 'value')]
)
def update_figures(selected_time_index):
    current_time = ohlc_data.index[selected_time_index]

    # Вычисляем конечные времена для каждого диапазона
    end_time1 = current_time - pd.Timedelta(seconds=args.range1)
    end_time2 = current_time - pd.Timedelta(seconds=args.range2)
    end_time3 = current_time - pd.Timedelta(seconds=args.range3)

    # Фильтруем данные для каждого диапазона
    tick_data1 = data.loc[end_time1:current_time]
    tick_data2 = data.loc[end_time2:current_time]
    tick_data3 = data.loc[end_time3:current_time]

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=ohlc_data.index,
        y=ohlc_data['close'],
        mode='lines',
        name='Close Price',
        line=dict(color='blue', width=1)
    ))

    # Точка текущей цены
    fig1.add_trace(go.Scatter(
        x=[current_time],
        y=[ohlc_data['close'].iloc[selected_time_index]],
        mode='markers',
        marker=dict(color='red', size=10),
        name='Current Point'
    ))

    # Добавляем точки для конца диапазона каждого из баров
    if not tick_data1.empty:
        fig1.add_trace(go.Scatter(
            x=[end_time1],
            y=[ohlc_data.asof(end_time1)['close']],
            mode='markers',
            marker=dict(color='green', size=8),
            name=f'End of Range {args.range1} sec'
        ))

    if not tick_data2.empty:
        fig1.add_trace(go.Scatter(
            x=[end_time2],
            y=[ohlc_data.asof(end_time2)['close']],
            mode='markers',
            marker=dict(color='orange', size=8),
            name=f'End of Range {args.range2} sec'
        ))

    if not tick_data3.empty:
        fig1.add_trace(go.Scatter(
            x=[end_time3],
            y=[ohlc_data.asof(end_time3)['close']],
            mode='markers',
            marker=dict(color='purple', size=8),
            name=f'End of Range {args.range3} sec'
        ))

    fig1.update_layout(
        xaxis=dict(
            range=[ohlc_data.index.min(), ohlc_data.index.max()],
            rangeslider=dict(visible=False)
        ),
        yaxis=dict(fixedrange=False),
        showlegend=False
    )

    fig2 = go.Figure()

    # Функция для добавления бара на график
    def add_bar(data, tick_data, x_pos, name, range_seconds):
        if not data.empty:
            open_price = data['open'].iloc[0]
            close_price = data['close'].iloc[-1]
            color = 'green' if close_price > open_price else 'red' if close_price < open_price else 'black'
            
            # Количество тиков в секунду
            tick_count = len(tick_data)
            ticks_per_second = round(tick_count / range_seconds)

            # Подсчет объемов с 'True' и 'False'
            true_volume = tick_data[tick_data.iloc[:, -2] == True].shape[0]  # True для бидов
            false_volume = tick_data[tick_data.iloc[:, -2] == False].shape[0]  # False для асков

            # Процентное соотношение
            total_volume = true_volume + false_volume
            true_percent = round((true_volume / total_volume) * 100) if total_volume > 0 else 0
            false_percent = round((false_volume / total_volume) * 100) if total_volume > 0 else 0

            # Вертикальная линия
            fig2.add_trace(go.Scatter(
                x=[x_pos, x_pos],
                y=[data['low'].min(), data['high'].max()],
                mode='lines',
                line=dict(color=color, width=2),
                name=name
            ))

            # Отметка для цены открытия
            fig2.add_trace(go.Scatter(
                x=[x_pos - 0.1, x_pos],
                y=[open_price, open_price],
                mode='lines',
                line=dict(color=color, width=2),
                showlegend=False
            ))

            # Отметка для цены закрытия
            fig2.add_trace(go.Scatter(
                x=[x_pos, x_pos + 0.1],
                y=[close_price, close_price],
                mode='lines',
                line=dict(color=color, width=2),
                showlegend=False
            ))

            # Определение цвета для процентов
            true_color = 'green' if true_percent > 50 else 'red' if true_percent < 50 else 'black'
            false_color = 'green' if false_percent > 50 else 'red' if false_percent < 50 else 'black'

            # Добавление аннотаций для процентного соотношения True и False
            fig2.add_annotation(
                x=x_pos - 0.2,  # Ближе к бару
                y=data['low'].min() - (data['high'].max() - data['low'].min()) * 0.3,  # Зафиксировано ниже
                text=f'{true_percent}',  # Убрана процентная метка
                showarrow=False,
                font=dict(color=true_color)
            )
            fig2.add_annotation(
                x=x_pos + 0.2,  # Ближе к бару
                y=data['low'].min() - (data['high'].max() - data['low'].min()) * 0.3,  # Зафиксировано ниже
                text=f'{false_percent}',  # Убрана процентная метка
                showarrow=False,
                font=dict(color=false_color)
            )

            # Добавление аннотации для количества тиков в секунду
            fig2.add_annotation(
                x=x_pos - 0.15,
                y=data['high'].max() + (data['high'].max() - data['low'].min()) * 0.2,
                text=str(ticks_per_second),
                showarrow=False,
                font=dict(color='black')
            )

    # Добавляем три бара для каждого временного диапазона
    add_bar(ohlc_data.loc[end_time3:current_time], tick_data3, 1, f'Bar {args.range3} sec', args.range3)
    add_bar(ohlc_data.loc[end_time2:current_time], tick_data2, 2, f'Bar {args.range2} sec', args.range2)
    add_bar(ohlc_data.loc[end_time1:current_time], tick_data1, 3, f'Bar {args.range1} sec', args.range1)

    fig2.update_layout(
        xaxis=dict(
            range=[0, 4],
            showticklabels=False,
            rangeslider=dict(visible=False)
        ),
        yaxis=dict(fixedrange=False),
        margin=dict(l=0, r=0, t=20, b=20),  # Окончательное оформление графика
        showlegend=False  # Убираем легенду
    )

    return fig1, fig2

if __name__ == '__main__':
    app.run_server(debug=True)
