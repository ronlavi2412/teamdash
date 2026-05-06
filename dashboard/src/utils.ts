export function createStripePattern(baseColor: string): CanvasPattern | string {
  const canvas = document.createElement('canvas');
  canvas.width = 8;
  canvas.height = 8;
  const ctx = canvas.getContext('2d');
  if (!ctx) return baseColor;

  ctx.fillStyle = baseColor + '40';
  ctx.fillRect(0, 0, 8, 8);

  ctx.strokeStyle = baseColor;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, 8);
  ctx.lineTo(8, 0);
  ctx.moveTo(-2, 2);
  ctx.lineTo(2, -2);
  ctx.moveTo(6, 10);
  ctx.lineTo(10, 6);
  ctx.stroke();

  return ctx.createPattern(canvas, 'repeat') ?? baseColor;
}

export function calculateAverage(values: (number | null)[]): number | null {
  const filtered = values.filter((v): v is number => v !== null && v !== undefined);
  if (filtered.length === 0) return null;
  return filtered.reduce((sum, v) => sum + v, 0) / filtered.length;
}

export function calculateMedian(values: (number | null)[]): number | null {
  const sorted = values
    .filter((v): v is number => v !== null)
    .sort((a, b) => a - b);
  if (!sorted.length) return null;
  const mid = Math.floor(sorted.length / 2);
  return +(sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2).toFixed(1);
}

export function getQuarterLabel(label: string, index: number, currentQuarterIndex: number, isCurrentQuarter: boolean): string {
  return isCurrentQuarter && index === currentQuarterIndex ? label + ' *' : label;
}
