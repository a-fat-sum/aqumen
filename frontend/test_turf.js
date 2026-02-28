import * as turf from '@turf/turf';

const center = [-122.1938, 47.6115];
const radius = 500;
const c1 = turf.circle(center, radius, { units: 'meters' });
const c2 = turf.circle(center, radius / 1000, { units: 'kilometers' });

console.log("Meters area:", turf.area(c1));
console.log("Kilometers area:", turf.area(c2));
