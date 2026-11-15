import {test} from "node:test";
import assert from "node:assert/strict";
import {newMeasure,quarters,regrid,splitMeasure,type Project} from "./model";

test("splitting a bar preserves crossing melody and carries harmony",()=>{
  const m=newMeasure(10,120,{numerator:4,denominator:4});
  m.chords=[{id:"chord",symbol:"Dm7",beat:0,confidence:1,manual:true}];
  m.notes=[{id:"note",beat:1,duration:2,midi:62,confidence:1,manual:true}];
  const [a,b]=splitMeasure(m);
  assert.equal(a.end,11);assert.equal(b.start,11);
  assert.equal(quarters(a.meter),2);assert.equal(a.notes[0].duration,1);
  assert.equal(b.notes[0].beat,0);assert.equal(b.notes[0].duration,1);
  assert.equal(b.chords[0].symbol,"Dm7");assert.notEqual(a.id,b.id);
});
test("grid correction preserves manual events and rejects truncation",()=>{
  const m=newMeasure(0,120,{numerator:4,denominator:4});
  m.chords=[{id:"c",beat:3,symbol:"G7b9",confidence:1,manual:true}];
  const p={measures:[m],bpm:120,meter:m.meter} as Project;
  const edited=regrid(p,60,m.meter,2);
  assert.equal(edited.measures[0].end,6);
  assert.equal(edited.measures[0].chords[0].symbol,"G7b9");
  assert.equal(m.start,0);
  assert.throws(()=>regrid(p,120,{numerator:3,denominator:4},0),/outside/);
});
