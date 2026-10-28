import assert from "node:assert/strict";
import { test } from "node:test";
import { subSolarPoint } from "./sun.js";

const near = (got, want, tol, what) => assert.ok(Math.abs(got - want) <= tol, `${what}: got ${got.toFixed(2)}, wanted ${want} within ${tol}`);

test("March equinox 2024: the sun is over the equator", () => {
  near(subSolarPoint(new Date("2024-03-20T03:06:00Z")).lat, 0, 0.1, "declination");
});

test("June solstice 2024: declination is the axial tilt", () => {
  near(subSolarPoint(new Date("2024-06-20T20:51:00Z")).lat, 23.44, 0.1, "declination");
});

test("December solstice 2024: declination is minus the axial tilt", () => {
  near(subSolarPoint(new Date("2024-12-21T09:21:00Z")).lat, -23.44, 0.1, "declination");
});

test("noon UTC on 1 January 2000 puts the sun near Greenwich, slightly east (equation of time)", () => {
  const p = subSolarPoint(new Date("2000-01-01T12:00:00Z"));
  near(p.lat, -23.0, 0.2, "declination");
  near(p.lon, 0.8, 0.5, "longitude");
});

test("the sub solar longitude moves west by 15 degrees per hour", () => {
  const a = subSolarPoint(new Date("2026-10-28T10:00:00Z")).lon, b = subSolarPoint(new Date("2026-10-28T11:00:00Z")).lon;
  near(a - b, 15, 0.05, "hourly drift");
});
