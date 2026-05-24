"""Strategy implementations. All strategies inherit from base.Strategy."""

from quant.strategies.base import Signal, Strategy, StrategyConfig
from quant.strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from quant.strategies.overnight_max import OvernightMAXConfig, OvernightMAXStrategy
from quant.strategies.stretched_vp import StretchedVPConfig, StretchedVPStrategy
from quant.strategies.tsmom import TSMOMConfig, TSMOMStrategy

__all__ = [
    "MeanReversionConfig",
    "MeanReversionStrategy",
    "OvernightMAXConfig",
    "OvernightMAXStrategy",
    "Signal",
    "Strategy",
    "StrategyConfig",
    "StretchedVPConfig",
    "StretchedVPStrategy",
    "TSMOMConfig",
    "TSMOMStrategy",
]
