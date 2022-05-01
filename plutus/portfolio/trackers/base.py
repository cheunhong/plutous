from plutus.models import Trade, Position, Account
from plutus.models.enums import AssetType
from plutus.configuration import config
from plutus import database as db
from datetime import datetime, timedelta
from typing import List, Optional
from sqlmodel import Session
import pandas as pd


TIMEZONE = config['timezone']


class BaseTracker:
    "Base Class for Trackers"

    def __init__(self, account_id: int):
        self.conn = db.engine.connect()
        self.session: Session = db.Session(expire_on_commit=False)
        self.account = Account(id=account_id).get(self.session)
        self.positions = []
        self.positions_df = pd.DataFrame()

        assert db.get_url().split('/')[-1] == 'finance_test'
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def close(self):
        self.session.close()
        self.conn.close()
        db.engine.dispose()

    def get_positions(self, asset_type: AssetType) -> List[Position]:
        self.positions = (
            self.account.active_positions
            .filter_by(asset_type=asset_type).all()
        )
        return self.positions

    def get_positions_df(self, asset_type: AssetType) -> pd.DataFrame:
        positions = self.get_positions(asset_type)
        self.positions_df = pd.DataFrame([_.dict() for _ in positions])
        return self.positions_df

    def fetch_latest_trade(self, asset_type: AssetType) -> Trade:
        return (
            self.account.trades
            .filter_by(asset_type=asset_type)
            .limit(1).first()
        )

    def get_last_transacted_at(
        self, asset_type: AssetType,
        since: Optional[datetime] = None,
    ) -> pd.Timestamp: 
        if not since:
            since = self.account.init_balance_at
        latest_trade = self.fetch_latest_trade(asset_type)
        if latest_trade is not None:
            if latest_trade.transacted_at > since:
                since = latest_trade.transacted_at
        return (
            pd.Timestamp(since)
            .tz_localize(TIMEZONE)
            .tz_convert('UTC')
        ) + timedelta(milliseconds=1)

        