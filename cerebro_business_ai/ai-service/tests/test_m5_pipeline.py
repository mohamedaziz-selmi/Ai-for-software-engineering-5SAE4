import pandas as pd

from data.m5_pipeline import add_lag_calendar_features, chronological_split, forecast_metrics


def fixture():
    dates = pd.date_range('2025-01-01', periods=70, freq='D')
    return pd.DataFrame({'item_id':['a']*70, 'store_id':['s']*70, 'date':dates, 'sales':range(70), 'sell_price':[10.0]*70})


def test_m5_features_are_shifted_and_split_chronologically():
    frame = fixture()
    featured = add_lag_calendar_features(frame)
    assert featured.loc[28, 'lag_1'] == 27
    assert featured.loc[28, 'rolling_mean_7'] < 28
    train, validation, test = chronological_split(frame, validation_days=7, test_days=7)
    assert train['date'].max() < validation['date'].min() < test['date'].min()


def test_forecast_metrics_are_real_numeric_values():
    result = forecast_metrics([1, 2, 4], [1, 3, 2])
    assert result['mae'] > 0 and result['rmse'] > 0 and result['wape'] > 0
