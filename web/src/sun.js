const RAD = Math.PI / 180;

/** Sub solar point (where the sun is overhead) for a date, from the low precision solar position series
 *  in the Astronomical Almanac. Good to about 0.01 degrees, which is far finer than a globe needs. */
export function subSolarPoint(date = new Date()) {
  const n = date.getTime() / 864e5 - 10957.5; // days since J2000.0
  const L = (280.46 + 0.9856474 * n) % 360;
  const g = (357.528 + 0.9856003 * n) * RAD;
  const lambda = (L + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * RAD;
  const eps = (23.439 - 0.0000004 * n) * RAD;
  const dec = Math.asin(Math.sin(eps) * Math.sin(lambda));
  const ra = Math.atan2(Math.cos(eps) * Math.sin(lambda), Math.cos(lambda));
  const gmstDeg = (280.46061837 + 360.98564736629 * n) % 360;
  let lon = ra / RAD - gmstDeg;
  lon = ((lon + 540) % 360) - 180;
  return { lat: dec / RAD, lon };
}
