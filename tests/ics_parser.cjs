/* Independent, pinned MPL-2.0 ICAL.js test tool; never loaded by ALFRED runtime. */
const fs=require('node:fs'),crypto=require('node:crypto'),path=require('node:path');
const parserPath=path.resolve(__dirname,'../artifacts/tools/ical/package/dist/ical.es5.cjs');
if(crypto.createHash('sha256').update(fs.readFileSync(parserPath)).digest('hex')!=='02b0ab420c2b3af5bd0829b12b8becdffdc2311e62070c381cc0c60b52b0b365')throw new Error('Run the pinned calendar test-tool setup; unexpected ICAL.js hash');
const ICAL=require(parserPath);
const input=fs.readFileSync(0,'utf8');
const parsed=ICAL.parse(input),component=new ICAL.Component(parsed);
if(component.name!=='vcalendar')throw new Error('Expected VCALENDAR');
const second=ICAL.parse(component.toString());
const canonical=value=>JSON.stringify(value);
if(canonical(parsed)!==canonical(second))throw new Error('Calendar import/export round-trip changed parsed data');
const events=component.getAllSubcomponents('vevent').map(event=>({
    uid:event.getFirstPropertyValue('uid'),summary:event.getFirstPropertyValue('summary'),
    start:event.getFirstPropertyValue('dtstart').toString(),end:event.getFirstPropertyValue('dtend').toString(),
    date:event.getFirstPropertyValue('dtstart').isDate,
    location:event.getFirstPropertyValue('location'),description:event.getFirstPropertyValue('description'),
    properties:event.getAllProperties().map(p=>p.name),components:event.getAllSubcomponents().map(c=>c.name),
}));
process.stdout.write(JSON.stringify({events,properties:component.getAllProperties().map(p=>p.name),roundtrip:true}));
