// Projects latitude/longitude onto the UK outline (viewBox 0 0 633 1049).
// Fitted to the outline's extremes (Lizard, Lowestoft, Fermanagh); Mercator in latitude.
const A = 62.68, B = 520.7;
const merc = (lat: number) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
// y = C * merc(lat) + D, fitted by least squares
const C = -3656.72, D = 4739.31;
export const project = (lat: number, lon: number) => ({ x: A * lon + B, y: C * merc(lat) + D });
