"""Backtesting engine."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from bot.core.models import (
    MarketData, Trade, Order, OrderStatus, 
    OrderType, Side, BacktestResult, Position
)
from bot.core.logger import get_logger
from bot.core.exceptions import BacktestError


class BacktestEngine:
    """Backtesting engine for strategy testing."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize backtest engine.
        
        Args:
            config: Backtest configuration
        """
        self.config = config
        self.logger = get_logger("backtest.engine")
        self.initial_capital = config.get('initial_capital', 10000.0)
        self.commission = config.get('commission', 0.001)
        self.slippage = config.get('slippage', 0.001)
        
        # Backtest state
        self.capital = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        self.equity_curve: List[float] = []
        self.drawdown_curve: List[float] = []
        self.max_equity = self.initial_capital
        self.max_drawdown = 0.0
    
    async def run_backtest(
        self,
        strategy,
        market_data: List[MarketData],
        symbol: str
    ) -> BacktestResult:
        """Run backtest on strategy.
        
        Args:
            strategy: Trading strategy
            market_data: Historical market data
            symbol: Trading symbol
            
        Returns:
            BacktestResult
        """
        self.logger.info(f"Starting backtest for {symbol}")
        self.logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        
        # Reset state
        self.capital = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.orders.clear()
        self.equity_curve = []
        self.drawdown_curve = []
        self.max_equity = self.initial_capital
        self.max_drawdown = 0.0
        
        # Process market data
        min_periods = strategy.get_min_periods() if hasattr(strategy, 'get_min_periods') else 100
        
        for i in range(min_periods, len(market_data)):
            # Get data window
            data_window = market_data[max(0, i - min_periods):i]
            current_candle = market_data[i]
            current_price = current_candle.close
            
            # Update equity
            self._update_equity(current_price, symbol)
            
            # Generate signal
            try:
                signal = await strategy.generate_signal(data_window, current_price)
                if signal:
                    self._execute_signal(signal, current_price, current_candle.timestamp, symbol)
            except Exception as e:
                self.logger.error(f"Error generating signal: {e}")
        
        # Close any open positions
        self._close_all_positions(market_data[-1].close, market_data[-1].timestamp, symbol)
        
        # Calculate results
        result = self._calculate_results(market_data[0].timestamp, market_data[-1].timestamp)
        
        self.logger.info(f"Backtest completed. Final capital: ${result.final_capital:,.2f}")
        self.logger.info(f"Total return: {result.total_return:.2%}")
        self.logger.info(f"Total trades: {result.total_trades}")
        self.logger.info(f"Win rate: {result.win_rate:.2%}")
        
        return result
    
    def _execute_signal(
        self,
        signal,
        price: float,
        timestamp: datetime,
        symbol: str
    ) -> None:
        """Execute trading signal.
        
        Args:
            signal: Trading signal
            price: Current price
            timestamp: Current timestamp
            symbol: Trading symbol
        """
        if signal.signal_type == 'hold':
            return
        
        if signal.signal_type == 'entry':
            self._open_position(signal, price, timestamp, symbol)
        elif signal.signal_type == 'exit':
            self._close_position(signal.side, price, timestamp, symbol)
    
    def _open_position(
        self,
        signal,
        price: float,
        timestamp: datetime,
        symbol: str
    ) -> None:
        """Open position.
        
        Args:
            signal: Trading signal
            price: Current price
            timestamp: Current timestamp
            symbol: Trading symbol
        """
        # Check if already in position
        if symbol in self.positions:
            return
        
        # Calculate position size (fixed 10% of capital)
        position_size = self.capital * 0.1
        quantity = position_size / price
        
        # Apply slippage
        execution_price = price * (1 + self.slippage) if signal.side == Side.BUY else price * (1 - self.slippage)
        
        # Calculate commission
        commission = position_size * self.commission
        
        # Deduct from capital
        self.capital -= commission
        
        # Create position
        position = Position(
            symbol=symbol,
            side=signal.side,
            quantity=quantity,
            entry_price=execution_price,
            current_price=execution_price,
            timestamp=timestamp,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        self.positions[symbol] = position
        self.logger.info(
            f"Opened {signal.side.value.upper()} position: "
            f"{quantity:.4f} {symbol} @ ${execution_price:.2f}"
        )
    
    def _close_position(
        self,
        side: Side,
        price: float,
        timestamp: datetime,
        symbol: str
    ) -> None:
        """Close position.
        
        Args:
            side: Side to close
            price: Current price
            timestamp: Current timestamp
            symbol: Trading symbol
        """
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        if position.side != side:
            return
        
        # Apply slippage
        execution_price = price * (1 - self.slippage) if side == Side.BUY else price * (1 + self.slippage)
        
        # Calculate PnL
        if side == Side.BUY:
            pnl = (execution_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - execution_price) * position.quantity
        
        # Calculate commission
        commission = position.value * self.commission
        
        # Update capital
        self.capital += position.value + pnl - commission
        
        # Create trade
        trade = Trade(
            id=f"trade_{len(self.trades) + 1}",
            order_id=f"order_{len(self.trades) + 1}",
            symbol=symbol,
            side=side,
            quantity=position.quantity,
            price=execution_price,
            timestamp=timestamp,
            commission=commission,
            realized_pnl=pnl
        )
        
        self.trades.append(trade)
        self.logger.info(
            f"Closed {side.value.upper()} position: "
            f"{position.quantity:.4f} {symbol} @ ${execution_price:.2f}, "
            f"PnL: ${pnl:.2f}"
        )
        
        # Remove position
        del self.positions[symbol]
    
    def _close_all_positions(self, price: float, timestamp: datetime, symbol: str) -> None:
        """Close all positions.
        
        Args:
            price: Current price
            timestamp: Current timestamp
            symbol: Trading symbol
        """
        if symbol in self.positions:
            position = self.positions[symbol]
            self._close_position(position.side, price, timestamp, symbol)
    
    def _update_equity(self, price: float, symbol: str) -> None:
        """Update equity curve.
        
        Args:
            price: Current price
            symbol: Trading symbol
        """
        equity = self.capital
        
        # Add unrealized PnL from open positions
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = price
            
            if position.side == Side.BUY:
                unrealized_pnl = (price - position.entry_price) * position.quantity
            else:
                unrealized_pnl = (position.entry_price - price) * position.quantity
            
            position.unrealized_pnl = unrealized_pnl
            equity += position.value + unrealized_pnl
        
        self.equity_curve.append(equity)
        
        # Update max equity and drawdown
        if equity > self.max_equity:
            self.max_equity = equity
            self.max_drawdown = 0.0
        else:
            drawdown = (self.max_equity - equity) / self.max_equity
            self.max_drawdown = max(self.max_drawdown, drawdown)
        
        self.drawdown_curve.append(self.max_drawdown)
    
    def _calculate_results(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Calculate backtest results.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            BacktestResult
        """
        if not self.trades:
            return BacktestResult(
                initial_capital=self.initial_capital,
                final_capital=self.capital,
                total_return=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                profit_factor=0.0,
                start_date=start_date,
                end_date=end_date,
                trades=[],
                equity_curve=self.equity_curve,
                drawdown_curve=self.drawdown_curve
            )
        
        winning_trades = [t for t in self.trades if t.realized_pnl > 0]
        losing_trades = [t for t in self.trades if t.realized_pnl <= 0]
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        win_rate = len(winning_trades) / len(self.trades)
        
        gross_profit = sum(t.realized_pnl for t in winning_trades)
        gross_loss = abs(sum(t.realized_pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calculate Sharpe ratio (simplified)
        if len(self.equity_curve) > 1:
            returns = [
                (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
                for i in range(1, len(self.equity_curve))
            ]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0.0
            
            # Sortino ratio
            negative_returns = [r for r in returns if r < 0]
            downside_std = np.std(negative_returns) if negative_returns else 0.0
            sortino_ratio = (avg_return / downside_std) * np.sqrt(252) if downside_std > 0 else 0.0
        else:
            sharpe_ratio = 0.0
            sortino_ratio = 0.0
        
        return BacktestResult(
            initial_capital=self.initial_capital,
            final_capital=self.capital,
            total_return=total_return,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            start_date=start_date,
            end_date=end_date,
            trades=self.trades,
            equity_curve=self.equity_curve,
            drawdown_curve=self.drawdown_curve
        )