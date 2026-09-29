let categoryChart, teamChart;
async function getJSON(url, opts){const r=await fetch(url, opts); if(!r.ok) throw new Error(await r.text()); return r.json();}
function card(label,value){return `<div class="card"><div class="label">${label}</div><div class="metric">${value}</div></div>`}
function chartData(rows){const months=[...new Set(rows.map(x=>x.month))].sort();const labels=[...new Set(rows.map(x=>x.label))].sort();return {labels:months,datasets:labels.map(label=>({label,data:months.map(m=>(rows.find(x=>x.month===m&&x.label===label)||{}).count||0),borderWidth:1}))}}
async function refresh(){
 const m=await getJSON('/api/v1/metrics/summary'); const s=m.summary;
 document.getElementById('cards').innerHTML=[card('Tickets',s.tickets.toLocaleString()),card('AI coverage',(100*s.classification_coverage).toFixed(1)+'%'),card('Avg confidence',s.avg_confidence==null?'—':(100*s.avg_confidence).toFixed(1)+'%'),card('Transfer cost','₹'+m.transfers.transfer_cost_inr.toLocaleString())].join('');
 const cat=await getJSON('/api/v1/metrics/monthly?dimension=ai_category'); const team=await getJSON('/api/v1/metrics/monthly?dimension=recommended_team');
 if(categoryChart)categoryChart.destroy();if(teamChart)teamChart.destroy();
 categoryChart=new Chart(document.getElementById('categoryChart'),{type:'bar',data:chartData(cat.data),options:{responsive:true,scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true}}}});
 teamChart=new Chart(document.getElementById('teamChart'),{type:'bar',data:chartData(team.data),options:{responsive:true,scales:{x:{stacked:true},y:{stacked:true,beginAtZero:true}}}});
 document.getElementById('signals').innerHTML=`<div class="signal">SLA breach rate<strong>${(100*m.sla.breach_rate).toFixed(1)}%</strong><small>₹${m.sla.breach_cost_inr.toLocaleString()} breach-credit exposure</small></div><div class="signal">Transfer rate<strong>${(100*m.transfers.transfer_rate).toFixed(1)}%</strong><small>${m.transfers.transfer_events} transfer events</small></div><div class="signal">Human review labels<strong>${m.evaluation.labels}</strong><small>Accuracy: ${m.evaluation.accuracy==null?'not measured':(100*m.evaluation.accuracy).toFixed(1)+'%'}</small></div>`;
 document.getElementById('evaluation').textContent=JSON.stringify(m.evaluation,null,2);
}
document.getElementById('run').onclick=async()=>{document.getElementById('run').disabled=true;document.getElementById('run').textContent='Running…';try{await getJSON('/api/v1/import',{method:'POST'});await getJSON('/api/v1/jobs/classify/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({limit:500})});await refresh();}catch(e){alert(e.message)}finally{document.getElementById('run').disabled=false;document.getElementById('run').textContent='Run analysis'}};
refresh().catch(console.error);
