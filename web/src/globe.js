// Entry point for the globe bundle: globe.gl plus the day and night layer, built on the same three.js copy.
import Globe from "globe.gl";
import { Color, Mesh, ShaderMaterial, SphereGeometry, Vector3 } from "three";

const RAD = Math.PI / 180;
const GLOBE_RADIUS = 100; // three-globe draws the earth with radius 100

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

const VERT = `
varying vec3 vNormal;
void main() {
  vNormal = normalize(position);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

// d is the sine of the sun's altitude at the surface point. Civil twilight ends at -6 degrees (d = -0.105)
// and astronomical twilight at -18 degrees (d = -0.309), so the shade deepens across that band.
const FRAG = `
uniform vec3 sun;
uniform vec3 tint;
uniform float strength;
varying vec3 vNormal;
void main() {
  float d = dot(normalize(vNormal), sun);
  float night = smoothstep(0.03, -0.32, d);
  gl_FragColor = vec4(tint, 0.56 * strength * night);
}`;

/** A thin shell over the globe that darkens the hemisphere facing away from the sun. */
export function createNightLayer(globe) {
  const material = new ShaderMaterial({
    uniforms: { sun: { value: new Vector3(1, 0, 0) }, tint: { value: new Color("#030b14") }, strength: { value: 1 } },
    vertexShader: VERT,
    fragmentShader: FRAG,
    transparent: true,
    depthWrite: false,
  });
  const shell = new Mesh(new SphereGeometry(GLOBE_RADIUS * 1.004, 96, 64), material);
  shell.renderOrder = 2;
  globe.scene().add(shell);

  function update(date = new Date()) {
    const p = subSolarPoint(date);
    const c = globe.getCoords(p.lat, p.lon, 0);
    material.uniforms.sun.value.set(c.x, c.y, c.z).normalize();
    return p;
  }
  /** 1 shows the full shade; lower values keep a night side island readable when the view is close. */
  function setStrength(v) { material.uniforms.strength.value = v; }
  return { update, setStrength, shell };
}

export { Globe };
