// Run the actual read-only scripts in an inert mongosh-shaped context.
// The small evaluator covers only the pipeline operators asserted below; it is
// not a MongoDB compatibility or integration test.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const calls = [];
const selected = {_id: 'run-a', manifest: {}, results: []};
function collection(name, run = selected) {
  return {
    aggregate(pipeline) { calls.push({name, pipeline}); return {toArray: () => []}; },
    find(filter) { calls.push({name, filter}); return {sort() {return this;}, limit() {return this;}, toArray: () => []}; },
    findOne(filter = {}) { calls.push({name, filter}); return run; },
  };
}
function execute(file, run = selected) {
  calls.length = 0;
  const db = new Proxy({}, {get: (_, name) => collection(name, run)});
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../queries', file), 'utf8'),
    {db, print() {}, printjson() {}, Date, Infinity}, {filename: file, timeout: 1000});
  return JSON.parse(JSON.stringify(calls));
}
function field(row, name) {return name.split('.').reduce((value, key) => value == null ? undefined : value[key], row);}
function expr(value, row) {
  if (typeof value === 'string' && value.startsWith('$')) return field(row, value.slice(1));
  if (!value || typeof value !== 'object' || value instanceof Date) return value;
  if (Array.isArray(value)) return value.map(x => expr(x, row));
  for (const [op, args] of Object.entries(value)) {
    if (op === '$subtract') {const [a,b] = expr(args,row); return a-b;}
    if (op === '$divide') {const [a,b] = expr(args,row); return a/b;}
    if (op === '$multiply') return expr(args,row).reduce((a,b) => a*b,1);
    if (op === '$eq') {const [a,b] = expr(args,row); return a===b;}
  }
  return Object.fromEntries(Object.entries(value).map(([k,v]) => [k,expr(v,row)]));
}
function matches(row, query) {
  return Object.entries(query).every(([key, value]) => {
    if (key === '$expr') return expr(value,row);
    const actual = field(row,key);
    if (!value || typeof value !== 'object') return actual === value;
    return Object.entries(value).every(([op, expected]) => {
      if(op==='$gt') return actual > expected;
      if(op==='$in') return expected.includes(actual);
      if(op==='$ne') return actual !== expected;
      if(op==='$type' && expected==='number') return typeof actual === 'number';
      if(op==='$exists') return (actual !== undefined) === expected;
      throw Error('unsupported match '+op);
    });
  });
}
function evaluate(pipeline, input) {
  let rows = input.map(x => ({...x}));
  for (const stage of pipeline) {
    if(stage.$match) rows = rows.filter(row => matches(row,stage.$match));
    else if(stage.$setWindowFields) {
      const spec = stage.$setWindowFields, groups = new Map();
      for(const row of rows) {
        const key = JSON.stringify(expr(spec.partitionBy,row));
        if(!groups.has(key)) groups.set(key,[]); groups.get(key).push(row);
      }
      rows = [];
      for(const group of groups.values()) {
        group.sort((a,b) => a.ts-b.ts);
        group.forEach((row,index) => {
          const result = {...row};
          for(const [key, value] of Object.entries(spec.output)) {
            if(value.$shift) result[key] = index ? expr(value.$shift.output,group[index-1]) : value.$shift.default;
            else if(value.$max) result[key] = Math.max(...group.slice(0,index+1).map(r => expr(value.$max,r)));
            else throw Error('unsupported window');
          }
          rows.push(result);
        });
      }
    } else if(stage.$sort) {
      const sort = Object.entries(stage.$sort);
      rows.sort((a,b) => {for(const [key,direction] of sort) {const x=field(a,key),y=field(b,key); if(x!==y)return (x<y?-1:1)*direction;} return 0;});
    } else if(stage.$addFields) rows = rows.map(row => ({...row,...Object.fromEntries(Object.entries(stage.$addFields).map(([k,v])=>[k,expr(v,row)]))}));
    else if(stage.$group) {
      const grouped = new Map();
      for(const row of rows) {
        const key = JSON.stringify(expr(stage.$group._id,row));
        if(!grouped.has(key)) grouped.set(key,[]); grouped.get(key).push(row);
      }
      rows = [...grouped.values()].map(group => {
        const out = {_id:expr(stage.$group._id,group[0])};
        for(const [key, spec] of Object.entries(stage.$group)) {
          if(key==='_id')continue;
          const [op,value]=Object.entries(spec)[0], values=group.map(row=>expr(value,row));
          if(op==='$sum')out[key]=values.reduce((a,b)=>a+b,0);
          else if(op==='$max')out[key]=Math.max(...values);
          else if(op==='$min')out[key]=Math.min(...values);
          else if(op==='$first')out[key]=values[0];
          else if(op==='$last')out[key]=values.at(-1);
          else throw Error('unsupported group '+op);
        }
        return out;
      });
    } else if(stage.$limit) rows = rows.slice(0,stage.$limit);
    else if(stage.$project) rows = rows.map(row=>Object.fromEntries(Object.entries(stage.$project).filter(([,v])=>v!==0).map(([k,v])=>[k,v===1?row[k]:expr(v,row)])));
    else throw Error('unsupported stage');
  }
  return rows;
}
const daily = execute('01-coins-and-bars.js').find(call => call.pipeline?.some(s=>s.$setWindowFields));
const series = {asset:'SOL',interval:'1d',source:'fixture',pair:'SOLUSD',frame_checksum:'same'};
const drops = evaluate(daily.pipeline,[{series,ts:86400000,close:100},{series,ts:172800000,close:90},{series,ts:345600000,close:9}]);
assert.equal(drops.length,1); assert.equal(drops[0].changePct,-9.999999999999998); assert.equal(drops[0].ts,172800000);
const reports = execute('05-backtests.js');
for(const call of reports.filter(x=>['equity_points','trades'].includes(x.name))) {
  const match=call.filter || call.pipeline[0].$match;
  assert.equal(match[call.name==='equity_points'?'curve.run_id':'run_id'],'run-a');
}
const equity = reports.find(x=>x.name==='equity_points' && x.pipeline);
const curves=evaluate(equity.pipeline,[{ts:1,curve:{strategy:'same',run_id:'run-a'},equity:100},{ts:2,curve:{strategy:'same',run_id:'run-a'},equity:110},{ts:3,curve:{strategy:'same',run_id:'run-b'},equity:1}]);
assert.equal(curves.length,1); assert.equal(curves[0].points,2); assert.equal(curves[0].last,110);
assert.equal(execute('05-backtests.js',null).filter(c=>c.name==='trades'||c.name==='equity_points').length,0);
const sweep=execute('06-experiments-and-pbo.js').find(x=>x.pipeline?.[0]?.$match?.kind==='sweep');
const rankings=evaluate(sweep.pipeline,[{kind:'sweep',section:'result',rankable:'True',label:'maintained-label',oos_sharpe:2,oos_trades:40},{kind:'sweep',section:'result',rankable:'False',label:'not-rankable',oos_sharpe:99,oos_trades:1},{kind:'cpcv',section:'result',strategy:'other',median_sharpe:100,total_trades:2}]);
assert.deepEqual(rankings,[{_id:'maintained-label',bestSharpe:2,configs:1,maxTrades:40}]);
console.log('query regressions passed: daily cadence, selected-run isolation, producer-shaped sweep, empty run');
