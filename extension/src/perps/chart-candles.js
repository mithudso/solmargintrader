// A display-only candle. Use real closed source minutes from the current interval.
export function formingChartCandle(history, step, now) {
  const latest = history.at(-1);
  const start = Math.floor(now / step) * step;
  if (!latest || latest.time < start || latest.time + 60 > now) return null;

  const count = (latest.time - start) / 60 + 1;
  const minutes = history.slice(-count);
  if (minutes.length !== count || minutes.some((row, i) => row.closed === false || row.time !== start + i * 60)) {
    return null;
  }

  const color = latest.close >= minutes[0].open ? '#39977b' : '#ac6469';
  return {
    through: latest.time + 60,
    candle: {
      time: start, open: minutes[0].open, close: latest.close,
      high: Math.max(...minutes.map(row => row.high)), low: Math.min(...minutes.map(row => row.low)),
      color, wickColor: color,
    },
  };
}
