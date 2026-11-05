/** Optional presentation build. Core financial calculations remain in Python.
 * Usage: node build_office.mjs REPO_ROOT OUTPUT_DIR PREVIEW_DIR
 * Requires @oai/artifact-tool in the authoring environment.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {Workbook, SpreadsheetFile, Presentation, PresentationFile} from '@oai/artifact-tool';

const [root, outputDir, previewDir] = process.argv.slice(2);
if (!root || !outputDir || !previewDir) throw new Error('Expected root, output and preview directories');
await fs.mkdir(outputDir, {recursive:true});
await fs.mkdir(previewDir, {recursive:true});
const d = JSON.parse(execFileSync(process.env.CAPITAL_PYTHON || 'python3', [path.join(root,'scripts/export_office_data.py')], {encoding:'utf8'}));
const green='#1B4332', ink='#17291F', muted='#58665E', font='Arial';
const money='#,##0.00;(#,##0.00);"—"';
const n = x => Number(x), pct = x => (n(x)*100).toFixed(2)+'%';
const label = s => s.toLowerCase().replaceAll('_',' ').replace(/^./,s=>s.toUpperCase());
const w=Workbook.create();
const review=w.worksheets.add('Capital review'), controls=w.worksheets.add('Disclosure controls');
for(const s of [review,controls]) {
  s.showGridLines=false;
  s.getRange('A1:I30').format.font={name:font,size:11,color:ink};
  s.getRange('A1:I30').format.rowHeight=24;
  s.getRange('A1:I30').format.columnWidth=17;
  s.getRange('A1:A30').format.columnWidth=31;
}
review.tabColor=green;
review.getRange('A2').values=[['Capital monitoring — scenario review']];
review.getRange('A2').format.font={name:font,size:16,bold:true,color:green};
review.getRange('A3').values=[['Historical calibration: 31 Dec 2024 | Hypothetical portfolio | MXN millions']];
review.getRange('A4').values=[['Run '+d.summary.run_id+' | Imported scenario outputs; ratio and headroom recalculate below']];
review.getRange('A6:H6').values=[['Scenario','Capital','Credit RWA','Market RWA','Operational RWA','Total RWA','ICAP','Headroom']];
review.getRange('J6:K6').values=[['Control','Value']];
review.getRange('J7:K8').values=[['Target ratio',n(d.config.target_ratio)],['Minimum reference',.08]];
review.getRange('J6:J9').format.columnWidth=22;
review.getRange('K7:K8').setNumberFormat('0.0%');
review.getRange('K7').format.font={name:font,size:11,color:'#0000FF'};
review.getRange('K7').dataValidation={rule:{type:'decimal',operator:'between',formula1:0.0001,formula2:.9999}};
for(let i=0;i<d.scenarios.length;i++) {
 const r=i+7,s=d.scenarios[i];
 review.getRange(`A${r}:E${r}`).values=[[label(s.scenario),n(s.eligible_capital),n(s.credit_rwa),n(s.market_rwa),n(s.operational_rwa)]];
 review.getRange(`F${r}:H${r}`).formulas=[[`=SUM(C${r}:E${r})`,`=IF(F${r}>0,B${r}/F${r},NA())`,`=IF(AND(ISNUMBER($K$7),$K$7>0,$K$7<1),B${r}-$K$7*F${r},NA())`]];
}
review.getRange('B7:F14').setNumberFormat(money);
review.getRange('H7:H14').setNumberFormat(money);
review.getRange('G7:G14').setNumberFormat('0.00%');
review.getRange('H7:H14').conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FDE8E7',font:{bold:true,color:'#9C2828'}}});
review.getRange('A17').values=[['Imported outputs are a snapshot. Change portfolio assumptions in the Python inputs and regenerate.']];
review.getRange('A18').values=[['10.5% is a monitoring target; fundamental/basic capital composition is not tested.']];
review.getRange('A19').values=[['Public facts establish scale only. No source-institution stress estimate or regulatory filing is implied.']];
controls.getRange('A2').values=[['Public disclosure reconciliation']];
controls.getRange('A2').format.font={name:font,size:16,bold:true,color:green};
controls.getRange('A3').values=[['Source: issuer 2025 financial statements, note 19 p. 40; RWA table explicitly unaudited.']];
controls.getRange('A4').values=[[d.source.url]];
controls.getRange('A6:G6').values=[['Date','Control','Observed','Expected','Difference','Tolerance','Status']];
controls.getRange('A1:A20').format.columnWidth=18;
controls.getRange('B1:B20').format.columnWidth=27;
for(let i=0;i<d.reconciliations.length;i++) {
 const r=i+7,c=d.reconciliations[i];
 controls.getRange(`A${r}:D${r}`).values=[[new Date(c.as_of+'T00:00:00Z'),c.control,n(c.observed),n(c.expected)]];
 controls.getRange(`E${r}`).formulas=[[`=C${r}-D${r}`]];
 controls.getRange(`F${r}`).values=[[n(c.tolerance)]];
 controls.getRange(`G${r}`).formulas=[[`=IF(ABS(E${r})<=F${r},"PASS","REVIEW")`]];
}
controls.getRange('A7:A14').setNumberFormat('dd-mmm-yy');
controls.getRange('C7:F14').setNumberFormat('0.000');
controls.getRange('G7:G14').conditionalFormats.add('containsText',{text:'REVIEW',format:{fill:'#FDE8E7',font:{bold:true,color:'#9C2828'}}});
controls.getRange('A17').values=[['RATIO_PROXY: percentage-point units. Other differences: MXN millions.']];
controls.getRange('A18').values=[['2025 remains unresolved; selecting it in the engine blocks stress execution.']];
controls.getRange('A19').values=[['A proxy mismatch may reflect a missing capital bridge; it is not proof of issuer error.']];
for(const [s,range] of [[review,'A6:H6'],[review,'J6:K6'],[controls,'A6:G6']]) {
 s.getRange(range).format={fill:green,font:{name:font,size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',wrapText:true,rowHeight:36};
}
w.recalculate();
// Independent agreement with Decimal engine, including middle and final rows.
for(let i=0;i<d.scenarios.length;i++) {
 const [ratio,headroom]=review.getRange(`G${i+7}:H${i+7}`).values[0];
 if(Math.abs(ratio-n(d.scenarios[i].icap))>1e-10 || Math.abs(headroom-n(d.scenarios[i].headroom))>1e-7) throw new Error('Workbook/engine disagreement');
}
// Disposable input-change check, then restore the authoritative target.
review.getRange('K7').values=[[.12]]; w.recalculate();
if(Math.abs(review.getRange('H7').values[0][0]-(6024-.12*39836))>1e-8) throw new Error('Target does not recalculate');
review.getRange('K7').values=[[n(d.config.target_ratio)]]; w.recalculate();
console.log((await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!',options:{useRegex:true,maxResults:20},maxChars:2000})).ndjson);
for(const [s,range,name] of [[review,'A1:K20','workbook-review'],[controls,'A1:G20','workbook-controls']]) {
 const b=await w.render({sheetName:s.name,range,scale:1.5,format:'png'});
 await fs.writeFile(path.join(previewDir,name+'.png'),new Uint8Array(await b.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(w)).save(path.join(outputDir,'capital_review.xlsx'));

const p=Presentation.create({slideSize:{width:1280,height:720}});
function text(s,name,value,left,top,width,height,size=24,color=ink,bold=false) {
 const x=s.shapes.add({name,geometry:'textbox',position:{left,top,width,height},fill:'none',line:{style:'solid',fill:'none',width:0}});
 x.text=value; x.text.style={fontSize:size,typeface:font,color,bold}; return x;
}
function slide(title,subtitle) {
 const s=p.slides.add(); s.background.fill='#F7F8F5';
 text(s,'eyebrow','FINANCE / CAPITAL MONITORING',56,32,1100,28,16,green,true);
 text(s,'headline',title,56,88,1168,100,42,ink,true);
 text(s,'subtitle',subtitle,56,185,1168,54,21,muted);
 text(s,'footer',`Hypothetical portfolio · MXN millions · Run ${d.summary.run_id}`,56,662,1100,30,14,muted);
 s.speakerNotes.text=`Source: ${d.source.url}. Printed pp. 5, 9, 40. RWA disclosures explicitly unaudited. Engine evidence: examples/base/manifest.json; run ${d.summary.run_id}. All exposures and shocks are assumed. Historical calibration 2024-12-31, not current institution stress results.`;
 return s;
}
function table(s,values,widths,top=270,height=300) {
 const t=s.tables.add({rows:values.length,columns:values[0].length,left:56,top,width:1168,height,values,columnWidths:widths});
 t.borders.assign({style:'solid',fill:'#D6DDD5',width:.7});
 for(let r=0;r<values.length;r++) for(let c=0;c<values[0].length;c++) {
  const cell=t.getCell(r,c); cell.fill=r===0?green:r%2?'#FFFFFF':'#EFF3ED';
  cell.text.style={typeface:font,fontSize:22,color:r===0?'#FFFFFF':ink,bold:r===0};
 }
 return t;
}
let s=slide('Capital headroom contracts under combined shocks','Historical 2024 calibration supports an explicit, reproducible stress exercise.');
const base=d.scenarios.find(x=>x.scenario==='BASELINE'), severe=d.scenarios.find(x=>x.scenario==='COMBINED_SEVERE');
for(const [i,value,caption] of [[0,pct(base.icap),'Baseline ICAP proxy'],[1,n(base.headroom).toLocaleString('en-US',{maximumFractionDigits:2}),'Headroom at 10.5% target'],[2,'2 / 8','Scenarios below target']]) {
 text(s,'metric-'+i,value,56+i*400,290,350,88,58,green,true);
 text(s,'caption-'+i,caption,56+i*400,388,350,65,24,ink);
}
text(s,'assessment',`Severe stress reduces the ratio to ${pct(severe.icap)}. Capital losses and RWA growth both contribute.`,56,510,1110,90,28,ink,true);
s=slide('Combined scenarios exhaust the monitoring buffer','Eight scenarios include market shocks, counterparty stress, expansion and distribution.');
table(s,[['Scenario','Capital','RWA','ICAP','Headroom'],...d.scenarios.map(x=>[label(x.scenario),n(x.eligible_capital).toFixed(1),n(x.total_rwa).toFixed(1),pct(x.icap),n(x.headroom).toFixed(1)])],[375,190,210,150,243],250,370);
s=slide('The severe case combines losses and denominator growth','An exact sequential bridge attributes the ICAP change without a residual.');
table(s,[['Component','Impact'],['Opening ICAP',pct(base.icap)],['Capital effect',n(severe.capital_effect_bp).toFixed(1)+' bp'],['RWA effect',n(severe.rwa_effect_bp).toFixed(1)+' bp'],['Closing ICAP',pct(severe.icap)]],[760,408],265,265);
text(s,'risk-note','Capital first at original RWA, then denominator change at stressed capital. Interaction effects follow this stated ordering.',56,555,1168,75,23,muted);
s=slide('Reverse stress identifies the target crossing','The result is a severity threshold on a specified adverse path, not a probability.');
text(s,'severity',n(d.reverse.severity).toFixed(3)+'×',56,285,380,105,72,green,true);
text(s,'severity-caption','Unit adverse scenario',56,400,400,45,25,ink);
text(s,'ray','1× severity: 20% FX depreciation; +200bp rates; 10% defaults; 20% credit migration; 25% market RWA growth.',510,285,680,165,28,ink);
text(s,'action','Review capital retention and incremental business RWA before distributions. Capital injection and RWA reduction are separate alternatives.',56,520,1168,90,27,ink,true);
s=slide('Source controls precede financial interpretation','One unresolved public-data proxy comparison is preserved for review.');
table(s,[['Disclosure check','2024','2025'],['Balance sheet','PASS','PASS'],['RWA components','PASS','PASS'],['Basic capital / equity','PASS','PASS'],['Basic capital / RWA vs reported ICAP','PASS','REVIEW']],[810,179,179],260,280);
text(s,'resolution','The 2025 proxy mismatch may reflect an undisclosed capital bridge. Selecting that date blocks stress execution; no reported figure is silently changed.',56,565,1168,75,24,muted);
s=slide('Model boundaries remain visible in the committee pack','Controls support reviewability; they do not replace capital eligibility or regulatory schedules.');
table(s,[['Implemented','Model boundary'],['Capital bridge, ICAP and headroom','Assumed deductions and Tier 2 eligibility'],['FX, rates and counterparty shocks','Hypothetical positions; linear DV01'],['Credit, market and operational RWA','Scenario overlays; no granular regulatory recomputation'],['42 tests and deterministic evidence','No desktop Office execution or regulatory submission']],[560,608],260,300);
text(s,'closing','Public financial data establish scale. Portfolio assumptions and stressed results belong to this independent model.',56,575,1168,70,24,ink,true);
for(const [i,s] of p.slides.items.entries()) {
 const b=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(previewDir,`slide-${i+1}.png`),new Uint8Array(await b.arrayBuffer()));
}
await (await PresentationFile.exportPptx(p)).save(path.join(outputDir,'capital_committee.pptx'));
console.log(JSON.stringify({run_id:d.summary.run_id,slides:p.slides.items.length,outputDir}));
