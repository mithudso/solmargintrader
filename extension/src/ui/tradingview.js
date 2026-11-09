import { el } from './ui-kit.js';

export function tradingViewUrl(asset, theme = 'dark') {
  if (!/^[A-Z0-9]{1,20}$/.test(asset)) throw new Error('Invalid chart symbol');
  const config = { autosize: true, symbol: `COINBASE:${asset}USD`, interval: '1', timezone: 'Etc/UTC',
    theme, style: '1', locale: 'en', allow_symbol_change: true, withdateranges: true,
    hide_side_toolbar: false, save_image: false, calendar: false, support_host: 'https://www.tradingview.com' };
  return 'https://www.tradingview-widget.com/embed-widget/advanced-chart/#' + encodeURIComponent(JSON.stringify(config));
}

export function renderTradingView(target, asset) {
  const theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
  const src = tradingViewUrl(asset, theme);
  if (target.dataset.src === src) return;
  target.dataset.src = src;
  const frame = el('iframe', { src, title: `TradingView ${asset}/USD chart`, loading: 'lazy',
    referrerPolicy: 'strict-origin-when-cross-origin', sandbox: 'allow-scripts allow-same-origin allow-popups' });
  target.replaceChildren(frame, el('a', { href: `https://www.tradingview.com/chart/?symbol=COINBASE%3A${asset}USD`,
    target: '_blank', rel: 'noopener noreferrer', text: `${asset}/USD reference chart by TradingView` }));
}
