import { freshStrategy } from '../public/evidence.js';

const forecast = freshStrategy({
  status: 'available',
  topStrategy: { expiresAt: 2_000_000_000, direction: 'up', label: 'fixture' },
}, 1_900_000_000);

if (forecast) {
  const direction: 'up' | 'down' | 'flat' = forecast.direction;
  const expiry: number = forecast.expiresAt;
  void direction;
  void expiry;
}

freshStrategy(null);
freshStrategy({ status: 'unavailable' });

// @ts-expect-error The public contract uses a numeric source expiry.
freshStrategy({ status: 'available', topStrategy: { expiresAt: 'later', direction: 'up' } });

// @ts-expect-error Unsupported directions cannot become a typed forecast.
freshStrategy({ status: 'available', topStrategy: { expiresAt: 2_000_000_000, direction: 'sideways' } });

// @ts-expect-error The evaluation clock uses numeric Unix seconds.
freshStrategy(null, 'tomorrow');
