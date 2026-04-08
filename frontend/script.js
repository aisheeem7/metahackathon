'use strict';
const DB = {
  get(key, fallback = null) { try { return JSON.parse(localStorage.getItem('fw_' + key)) ?? fallback; } catch { return fallback; } },
  set(key, val) { localStorage.setItem('fw_' + key, JSON.stringify(val)); },
  del(key) { localStorage.removeItem('fw_' + key); }
};

let currentUser = null, expenses = [], budgetLimits = {}, currentView = 'dashboard';
let expenseChart = null, categoryChart = null, budgetRing = null, analyticsChart = null, analyticsCatChart = null;
let chartPeriod = 7, selectedCat = 'Food & Dining', selectedType = 'debit', editCat = 'Other', editType = 'debit';
let autoSmsEnabled = false, smsTimer = null;

const CAT_ICONS = { 'Food & Dining':'🍽️','Transport':'🚌','Shopping':'🛍️','Entertainment':'🎬','Health':'💊','Bills':'📄','Education':'📚','Income':'💰','Other':'📦' };
const COLORS = ['#6366F1','#22C55E','#F59E0B','#EF4444','#8B5CF6','#EC4899','#14B8A6','#F97316','#94A3B8'];

const SUGGESTIONS = {
  safe: [
    { icon: '🎉', text: "You're crushing it! Well within your daily budget." },
    { icon: '💰', text: 'Great discipline! At this rate, you could save ₹1,500+ this week.' },
    { icon: '📈', text: 'Consider moving savings to a high-yield account like Paytm Money.' },
  ],
  near: [
    { icon: '⚡', text: "You've used over 80% of today's budget. Slow down on spending." },
    { icon: '🍱', text: 'Skip the next food order — make something at home instead.' },
    { icon: '🧾', text: 'Review your last few transactions. Spot any impulse buys?' },
  ],
  over: [
    { icon: '🚨', text: "You've exceeded today's budget. Avoid further purchases today." },
    { icon: '🍳', text: 'Cook at home tonight — save ₹150–₹400 vs ordering in.' },
    { icon: '🚶', text: 'Walk or take public transport to save ₹100–₹300.' },
    { icon: '📱', text: 'Audit your subscriptions — unused apps may cost ₹500+/month.' },
  ]
};

const ALL_BADGES = [
  { id: 'firstentry', emoji: '✍️', title: 'First Step', desc: 'Log your very first expense.', condition: () => expenses.filter(e=>e.type!=='credit').length >= 1 },
  { id: 'saver', emoji: '🏅', title: 'Saver', desc: 'Spend ≤ 75% of daily limit.', condition: () => getTodaySpend() <= getDailyLimit() * 0.75 },
  { id: 'streak3', emoji: '🔥', title: '3-Day Streak', desc: 'Under budget 3 days in a row.', condition: () => getStreak() >= 3 },
  { id: 'streak7', emoji: '⚡', title: 'Week Warrior', desc: 'Under budget 7 days in a row.', condition: () => getStreak() >= 7 },
  { id: 'hero', emoji: '🏆', title: 'Budget Hero', desc: 'Under budget for 5+ consecutive days.', condition: () => getStreak() >= 5 },
  { id: 'frugal', emoji: '💎', title: 'Frugal Master', desc: 'Spend less than ₹100 in a day.', condition: () => { const s=getTodaySpend(); return s>0&&s<100; } },
];

const FAKE_SMS = [
  "Rs. 250 has been debited from your HDFC account ending 1234 for Swiggy order.",
  "Your a/c XXXX5678 is debited for Rs 120.00 by Uber rides on 07/04/2026.",
  "Amount of Rs. 450.50 paid to Amazon Shopping via UPI Ref 927461.",
  "Rs. 80 deducted from SBI Acct XXXXXXX765 at Cafe Coffee Day.",
  "INR 1500 transferred to Apollo Pharmacy UPI 765432.",
  "Rs 25000 credited to your HDFC account by NEFT from EMPLOYER PAYROLL.",
  "Paid Rs. 340 to PVR Cinemas on 07/04/2026 via UPI.",
];

const SMS_PATTERNS = [
  /(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)\s*(?:has\s+been\s+)?(?:debited|deducted|paid|transferred)/i,
  /(?:debited|deducted|paid|transferred)\s+(?:of\s+|by\s+|for\s+)?(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)/i,
  /(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+paid/i,
  /(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)\s+credited/i,
  /(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)/i,
];
const SMS_CATS = {
  'Food & Dining': ['swiggy','zomato','food','restaurant','cafe','coffee','dining','meal','bakery','pizza','burger','dominos','mcdonalds','kfc','biryani'],
  'Transport': ['uber','ola','rapido','metro','bus','train','irctc','cab','taxi','auto','petrol','fuel','parking','fastag'],
  'Shopping': ['amazon','flipkart','myntra','ajio','nykaa','meesho','mall','store','shop','market','dmart'],
  'Entertainment': ['netflix','spotify','prime','hotstar','jiocinema','cinema','pvr','inox','movie','game'],
  'Health': ['pharmacy','medplus','hospital','clinic','apollo','netmeds','1mg','medicine'],
  'Bills': ['electricity','gas','broadband','airtel','jio','bsnl','vodafone','bill','recharge','mobile','dth'],
  'Education': ['udemy','coursera','school','college','university','books','byju','unacademy'],
};

function fmt(n) { return '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 }); }
function today() { return new Date().toISOString().split('T')[0]; }
function fmtDate(d) { return new Date(d+'T00:00:00').toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }); }
function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2); }
function clamp(v,lo,hi) { return Math.max(lo,Math.min(hi,v)); }
function setText(id,val) { const el=document.getElementById(id); if(el) el.textContent=val; }
function setVal(id,val) { const el=document.getElementById(id); if(el) el.value=val; }
function greeting() { const h=new Date().getHours(); return h<12?'Good morning':h<17?'Good afternoon':'Good evening'; }
function getDailyLimit() { return currentUser?.dailyLimit || budgetLimits?.daily || 500; }
function getTodaySpend() { return expenses.filter(e=>e.date===today()&&e.type!=='credit').reduce((s,e)=>s+e.amount,0); }
function getTotalIncome() { return expenses.filter(e=>e.type==='credit').reduce((s,e)=>s+e.amount,0); }
function getTotalExpenses() { return expenses.filter(e=>e.type!=='credit').reduce((s,e)=>s+e.amount,0); }
function getMonthSpend() { const m=today().slice(0,7); return expenses.filter(e=>e.date.startsWith(m)&&e.type!=='credit').reduce((s,e)=>s+e.amount,0); }
function getStreak() {
  const limit=getDailyLimit(); let streak=0; const d=new Date();
  for(let i=0;i<30;i++) {
    const key=d.toISOString().split('T')[0];
    const spent=expenses.filter(e=>e.date===key&&e.type!=='credit').reduce((s,e)=>s+e.amount,0);
    if(spent>0&&spent<=limit) { streak++; d.setDate(d.getDate()-1); } else break;
  }
  return streak;
}
function getSpendByDay(days) {
  const result=[],labels=[];
  for(let i=days-1;i>=0;i--) {
    const d=new Date(); d.setDate(d.getDate()-i);
    const key=d.toISOString().split('T')[0];
    result.push(expenses.filter(e=>e.date===key&&e.type!=='credit').reduce((s,e)=>s+e.amount,0));
    labels.push(d.toLocaleDateString('en-IN',{day:'2-digit',month:'short'}));
  }
  return {labels,data:result};
}
function getSpendByCategory(expList) {
  const cats={};
  (expList||expenses).filter(e=>e.type!=='credit').forEach(e=>{ cats[e.category]=(cats[e.category]||0)+e.amount; });
  return cats;
}
function getEarnedBadges() { return ALL_BADGES.filter(b=>{ try{return b.condition();}catch{return false;} }); }
function detectCategory(text) {
  const lower=text.toLowerCase();
  for(const [cat,kws] of Object.entries(SMS_CATS)) { if(kws.some(k=>lower.includes(k))) return cat; }
  return 'Other';
}
function parseSms(text) {
  let amount=null;
  for(const p of SMS_PATTERNS) { const m=text.match(p); if(m) { amount=parseFloat(m[1].replace(/,/g,'')); if(!isNaN(amount)&&amount>0) break; } }
  if(!amount) return null;
  const isCredit=/credited|received|credit/i.test(text);
  const type=isCredit?'credit':'debit';
  const category=isCredit?'Income':detectCategory(text);
  let merchant='';
  const mp=[/(?:to|at|for)\s+([A-Za-z][A-Za-z0-9\s&.'-]{2,25?}?)\s*(?:via|on|using|ref|upi|txn|\.|$)/i,/paid\s+to\s+([A-Za-z][A-Za-z0-9\s&.'-]{2,25?}?)\s*(?:via|for|\.|$)/i];
  for(const p of mp) { const m=text.match(p); if(m) { merchant=m[1].trim(); break; } }
  return {amount,type,category,merchant};
}

// ── AUTH ──
function showAuthPage(id) { document.querySelectorAll('.auth-page').forEach(p=>p.classList.remove('active')); document.getElementById(id)?.classList.add('active'); }
function togglePw(inputId,btn) {
  const inp=document.getElementById(inputId); if(!inp) return;
  const eyeOpen=`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const eyeClosed=`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
  if(inp.type==='password'){inp.type='text';btn.innerHTML=eyeClosed;} else{inp.type='password';btn.innerHTML=eyeOpen;}
}
document.addEventListener('input',e=>{
  if(e.target.id!=='signup-password') return;
  const val=e.target.value, fill=document.getElementById('pw-strength-fill'); if(!fill) return;
  let s=0; if(val.length>=8)s++; if(/[A-Z]/.test(val))s++; if(/[0-9]/.test(val))s++; if(/[^A-Za-z0-9]/.test(val))s++;
  fill.style.width=(s/4*100)+'%'; fill.style.background=['#EF4444','#F59E0B','#22C55E','#22C55E'][s-1]||'#E2E8F0';
});
function showFieldErr(id,msg){const el=document.getElementById(id);if(el){el.textContent=msg;el.style.display='block';}}
function clearFieldErr(id){const el=document.getElementById(id);if(el)el.textContent='';}
function loginUser(user,email) { DB.set('session',email.toLowerCase()); currentUser=user; autoSmsEnabled=DB.get('sms_'+currentUser.email,false); loadUserData(); showApp(); }
function signOut() { DB.del('session'); currentUser=null; expenses=[]; budgetLimits={}; stopSmsSimulator(); document.getElementById('app-shell').classList.add('hidden'); document.getElementById('auth-wrapper').classList.remove('hidden'); showAuthPage('page-signin'); toast('Signed out successfully.','success'); }
function initAuth() {
  document.getElementById('signin-form')?.addEventListener('submit',e=>{
    e.preventDefault();
    const email=document.getElementById('signin-email').value.trim(), pw=document.getElementById('signin-password').value;
    let ok=true;
    if(!email||!/\S+@\S+\.\S+/.test(email)){showFieldErr('signin-email-err','Valid email required.');ok=false;}else clearFieldErr('signin-email-err');
    if(!pw||pw.length<6){showFieldErr('signin-pw-err','Min 6 characters.');ok=false;}else clearFieldErr('signin-pw-err');
    if(!ok) return;
    const users=DB.get('users',{}), user=users[email.toLowerCase()];
    if(!user||user.password!==btoa(pw)){showFieldErr('signin-pw-err','Invalid email or password.');return;}
    loginUser(user,email);
  });
  document.getElementById('signup-form')?.addEventListener('submit',e=>{
    e.preventDefault();
    const fname=document.getElementById('signup-fname').value.trim(), lname=document.getElementById('signup-lname').value.trim();
    const email=document.getElementById('signup-email').value.trim(), limit=parseFloat(document.getElementById('signup-daily-limit').value), pw=document.getElementById('signup-password').value;
    let ok=true;
    if(!fname){showFieldErr('signup-fname-err','First name required.');ok=false;}else clearFieldErr('signup-fname-err');
    if(!email||!/\S+@\S+\.\S+/.test(email)){showFieldErr('signup-email-err','Valid email required.');ok=false;}else clearFieldErr('signup-email-err');
    if(!pw||pw.length<8){showFieldErr('signup-pw-err','Min 8 characters.');ok=false;}else clearFieldErr('signup-pw-err');
    if(!ok) return;
    const users=DB.get('users',{});
    if(users[email.toLowerCase()]){showFieldErr('signup-email-err','Account already exists.');return;}
    const newUser={fname,lname,email:email.toLowerCase(),dailyLimit:isNaN(limit)||limit<1?500:limit,phone:'',password:btoa(pw),joinDate:new Date().toISOString()};
    users[email.toLowerCase()]=newUser; DB.set('users',users);
    toast('Account created! Welcome.','success'); loginUser(newUser,email);
  });
}
function loadUserData() { const k=currentUser.email; expenses=DB.get('expenses_'+k,[]); budgetLimits=DB.get('budgets_'+k,{daily:currentUser.dailyLimit||500}); currentUser.dailyLimit=budgetLimits.daily||currentUser.dailyLimit||500; }
function saveUserData() { const k=currentUser.email; DB.set('expenses_'+k,expenses); DB.set('budgets_'+k,budgetLimits); const users=DB.get('users',{}); users[currentUser.email]=currentUser; DB.set('users',users); }
function checkSession() { const s=DB.get('session'); if(s){const u=DB.get('users',{})[s];if(u){currentUser=u;loadUserData();showApp();return;}} showAuthPage('page-signin'); }
function showApp() {
  document.getElementById('auth-wrapper').classList.add('hidden');
  document.getElementById('app-shell').classList.remove('hidden');
  updateSidebarUser(); updateTopbarDate();
  const tog=document.getElementById('sms-toggle');
  if(tog) tog.classList.toggle('on',autoSmsEnabled);
  updateSmsChip();
  if(autoSmsEnabled) startSmsSimulator();
  const permShown=DB.get('sms_perm_shown_'+currentUser.email,false);
  if(!permShown) { setTimeout(()=>showSmsPermModal(),1500); }
  navigate('dashboard');
}

// ── NAVIGATION ──
const VIEW_TITLES = { dashboard:'Dashboard', transactions:'Transactions', expenses:'Add Transaction', analytics:'Analytics', budget:'Budget', badges:'Badges', profile:'Profile' };
function navigate(view) {
  currentView=view;
  document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
  document.getElementById('view-'+view)?.classList.add('active');
  document.querySelectorAll('.nav-link,.bnav-link').forEach(l=>l.classList.remove('active'));
  document.getElementById('nav-'+view)?.classList.add('active');
  document.getElementById('bnav-'+view)?.classList.add('active');
  setText('topbar-title', VIEW_TITLES[view]||'');
  if(view==='dashboard') renderDashboard();
  else if(view==='transactions') renderTransactions();
  else if(view==='expenses') renderExpenseView();
  else if(view==='analytics') renderAnalytics();
  else if(view==='budget') renderBudgetView();
  else if(view==='badges') renderBadges();
  else if(view==='profile') renderProfile();
  closeSidebar();
}
function toggleSidebar() {
  const sb=document.getElementById('sidebar'); let ov=document.getElementById('sidebar-overlay');
  if(!ov){ov=document.createElement('div');ov.id='sidebar-overlay';ov.className='sidebar-overlay';ov.onclick=closeSidebar;document.body.appendChild(ov);}
  sb.classList.toggle('open'); ov.classList.toggle('show');
}
function closeSidebar() { document.getElementById('sidebar')?.classList.remove('open'); document.getElementById('sidebar-overlay')?.classList.remove('show'); }
function updateSidebarUser() {
  if(!currentUser) return;
  const init=(currentUser.fname?.[0]||'?').toUpperCase();
  document.getElementById('sidebar-avatar').textContent=init;
  const ta=document.getElementById('topbar-avatar'); if(ta) ta.textContent=init;
  setText('sidebar-user-name',(currentUser.fname||'')+' '+(currentUser.lname||''));
  setText('sidebar-user-email',currentUser.email||'');
}
function updateTopbarDate() { const el=document.getElementById('topbar-date'); if(el) el.textContent=new Date().toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'}); }
function updateSmsChip() {
  const chip=document.getElementById('sms-status-chip'), txt=document.getElementById('sms-status-text');
  if(!chip||!txt) return;
  if(autoSmsEnabled){chip.classList.add('active');txt.textContent='SMS Active';}
  else{chip.classList.remove('active');txt.textContent='SMS Off';}
}

// ── DASHBOARD ──
function renderDashboard() {
  const limit=getDailyLimit(), todayAmt=getTodaySpend(), income=getTotalIncome(), totalExp=getTotalExpenses(), monthAmt=getMonthSpend();
  const netBalance=income-totalExp, pct=clamp((todayAmt/limit)*100,0,100);
  setText('dash-greeting',greeting()+', '+(currentUser?.fname||'there'));
  setText('stat-balance',fmt(netBalance));
  setText('stat-balance-sub','Credits − Debits');
  setText('stat-today',fmt(todayAmt));
  setText('stat-today-sub','of '+fmt(limit)+' limit');
  setText('stat-month',fmt(monthAmt));
  setText('stat-income',fmt(income));
  const bar=document.getElementById('stat-today-bar');
  if(bar){bar.style.width=pct+'%';bar.style.background=pct>100?'var(--red)':pct>80?'var(--amber)':'var(--accent)';}
  setText('dash-badge-count',getEarnedBadges().length+' badges');
  renderAlert(todayAmt,limit);
  renderSuggestions(todayAmt,limit);
  renderExpenseChart(chartPeriod);
  renderCategoryChart();
  renderRecentTransactions();
}
function renderAlert(spent,limit) {
  const banner=document.getElementById('alert-banner'); if(!banner) return;
  const pct=(spent/limit)*100;
  if(pct>150){banner.className='alert-banner danger';setText('alert-title','Severe Overspend');setText('alert-msg',`You've spent ${fmt(spent)}, which is ${Math.round(pct-100)}% over your ${fmt(limit)} daily limit.`);banner.classList.remove('hidden');}
  else if(pct>100){banner.className='alert-banner warning';setText('alert-title','Daily Budget Exceeded');setText('alert-msg',`You've spent ${fmt(spent)} against a ${fmt(limit)} limit. Try to hold back.`);banner.classList.remove('hidden');}
  else if(pct>80){banner.className='alert-banner warning';setText('alert-title','Approaching Limit');setText('alert-msg',`You've used ${Math.round(pct)}% of today's budget. ${fmt(limit-spent)} remaining.`);banner.classList.remove('hidden');}
  else banner.classList.add('hidden');
}
function dismissAlert() { document.getElementById('alert-banner')?.classList.add('hidden'); }
function renderSuggestions(spent,limit) {
  const pct=(spent/limit)*100, list=document.getElementById('suggestions-list'), tag=document.getElementById('suggestion-status-tag');
  if(!list||!tag) return;
  let pool;
  if(pct>100){pool=SUGGESTIONS.over;tag.textContent='Over Budget';tag.className='badge-tag danger';}
  else if(pct>75){pool=SUGGESTIONS.near;tag.textContent='Near Limit';tag.className='badge-tag warning';}
  else{pool=SUGGESTIONS.safe;tag.textContent='On Track';tag.className='badge-tag';}
  list.innerHTML=pool.map(s=>`<div class="suggestion-item"><span class="suggestion-icon">${s.icon}</span><span>${s.text}</span></div>`).join('');
}
function renderRecentTransactions() {
  const el=document.getElementById('transactions-list'); if(!el) return;
  const sorted=[...expenses].sort((a,b)=>b.date.localeCompare(a.date)||b.id.localeCompare(a.id)).slice(0,6);
  if(!sorted.length){el.innerHTML=`<p class="empty-state">No transactions yet. <a href="#" onclick="navigate('expenses')">Add your first one →</a></p>`;return;}
  el.innerHTML=sorted.map(e=>txnRowHtml(e,false)).join('');
}
function txnRowHtml(e,showActions=true) {
  const isCredit=e.type==='credit';
  const amtClass=isCredit?'txn-amount credit':'txn-amount';
  const amtPrefix=isCredit?'+':'-';
  const iconClass=isCredit?'txn-icon credit-icon':'txn-icon';
  const actions=showActions?`<div class="txn-actions"><button class="txn-edit-btn" onclick="openEditModal('${e.id}')">Edit</button><button class="txn-del-btn" onclick="deleteTransaction('${e.id}')">Del</button></div>`:'';
  return `<div class="txn-row" id="txn-${e.id}">
    <div class="txn-left">
      <div class="${iconClass}">${CAT_ICONS[e.category]||'📦'}</div>
      <div>
        <div class="txn-name">${e.note||e.category}</div>
        <div class="txn-cat"><span class="txn-type-chip ${isCredit?'credit':'debit'}">${isCredit?'Credit':'Debit'}</span> ${e.category}</div>
      </div>
    </div>
    <div class="txn-right">
      <div class="${amtClass}">${amtPrefix}${fmt(e.amount)}</div>
      <div class="txn-date">${fmtDate(e.date)}</div>
      ${actions}
    </div>
  </div>`;
}

// ── CHARTS ──
function renderExpenseChart(days) {
  const {labels,data}=getSpendByDay(days), limit=getDailyLimit(), ctx=document.getElementById('expenseChart');
  if(!ctx) return;
  const colors=data.map(v=>v>limit?'rgba(239,68,68,.75)':v>limit*0.8?'rgba(245,158,11,.75)':'rgba(99,102,241,.75)');
  if(expenseChart) expenseChart.destroy();
  expenseChart=new Chart(ctx,{type:'bar',data:{labels,datasets:[{label:'Spent (₹)',data,backgroundColor:colors,borderRadius:6,borderSkipped:false},{label:'Daily Limit',data:Array(days).fill(limit),type:'line',borderColor:'rgba(239,68,68,.4)',borderDash:[6,4],borderWidth:1.5,pointRadius:0,fill:false}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>(c.dataset.label==='Daily Limit'?'Limit: ':'Spent: ')+fmt(c.parsed.y)}}},scales:{x:{grid:{display:false},ticks:{font:{family:'Inter',size:10},color:'#94A3B8'}},y:{grid:{color:'#F1F5F9'},ticks:{font:{family:'Inter',size:10},color:'#94A3B8',callback:v=>'₹'+v.toLocaleString('en-IN')},beginAtZero:true}}}});
}
function renderCategoryChart() {
  const cats=getSpendByCategory(), ctx=document.getElementById('categoryChart');
  if(!ctx) return;
  const labels=Object.keys(cats), data=Object.values(cats);
  if(!labels.length){if(categoryChart){categoryChart.destroy();categoryChart=null;}ctx.parentElement.innerHTML=`<p class="empty-state" style="padding:2rem 0">No data yet.</p>`;return;}
  if(categoryChart) categoryChart.destroy();
  categoryChart=new Chart(ctx,{type:'doughnut',data:{labels,datasets:[{data,backgroundColor:COLORS.slice(0,labels.length),borderWidth:2,borderColor:'#fff'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{font:{family:'Inter',size:10},color:'#475569',padding:8,boxWidth:10}},tooltip:{callbacks:{label:c=>c.label+': '+fmt(c.parsed)}}},cutout:'62%'}});
}
function setChartPeriod(days,btn) {
  chartPeriod=days;
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderExpenseChart(days);
}
function renderBudgetRing() {
  const limit=getDailyLimit(),spent=getTodaySpend(),pct=clamp((spent/limit)*100,0,100),ctx=document.getElementById('budgetRing');
  if(!ctx) return;
  const color=pct>100?'#EF4444':pct>80?'#F59E0B':'#6366F1';
  if(budgetRing) budgetRing.destroy();
  budgetRing=new Chart(ctx,{type:'doughnut',data:{datasets:[{data:[spent,Math.max(0,limit-spent)],backgroundColor:[color,'#E2E8F0'],borderWidth:0}]},options:{responsive:false,plugins:{legend:{display:false},tooltip:{enabled:false}},cutout:'75%'}});
  setText('ring-pct',Math.round(pct)+'%');
}

// ── TRANSACTIONS VIEW ──
function renderTransactions() {
  filterTransactions();
}
function filterTransactions() {
  const search=(document.getElementById('txn-search')?.value||'').toLowerCase();
  const typeF=document.getElementById('txn-filter-type')?.value||'';
  const catF=document.getElementById('txn-filter-cat')?.value||'';
  const period=document.getElementById('txn-filter-period')?.value||'30';
  let list=[...expenses].sort((a,b)=>b.date.localeCompare(a.date)||b.id.localeCompare(a.id));
  if(period!=='all'){const cutoff=new Date();cutoff.setDate(cutoff.getDate()-parseInt(period));list=list.filter(e=>new Date(e.date+'T00:00:00')>=cutoff);}
  if(typeF) list=list.filter(e=>(typeF==='credit'?e.type==='credit':e.type!=='credit'));
  if(catF) list=list.filter(e=>e.category===catF);
  if(search) list=list.filter(e=>(e.note||'').toLowerCase().includes(search)||e.category.toLowerCase().includes(search)||String(e.amount).includes(search));
  const totalDebit=list.filter(e=>e.type!=='credit').reduce((s,e)=>s+e.amount,0);
  const totalCredit=list.filter(e=>e.type==='credit').reduce((s,e)=>s+e.amount,0);
  const sumBar=document.getElementById('txn-summary-bar');
  if(sumBar) sumBar.innerHTML=`<div class="txn-sum-item"><div class="txn-sum-label">Transactions</div><div class="txn-sum-value">${list.length}</div></div><div class="txn-sum-item"><div class="txn-sum-label">Total Debit</div><div class="txn-sum-value debit">-${fmt(totalDebit)}</div></div><div class="txn-sum-item"><div class="txn-sum-label">Total Credit</div><div class="txn-sum-value credit">+${fmt(totalCredit)}</div></div><div class="txn-sum-item"><div class="txn-sum-label">Net</div><div class="txn-sum-value ${totalCredit-totalDebit>=0?'credit':'debit'}">${totalCredit-totalDebit>=0?'+':'-'}${fmt(Math.abs(totalCredit-totalDebit))}</div></div>`;
  const el=document.getElementById('txn-full-list');
  if(!el) return;
  if(!list.length){el.innerHTML=`<p class="empty-state">No transactions found. Try adjusting your filters.</p>`;return;}
  el.innerHTML=list.map(e=>txnRowHtml(e,true)).join('');
}
function clearTxnFilters() {
  setVal('txn-search',''); setVal('txn-filter-type',''); setVal('txn-filter-cat',''); setVal('txn-filter-period','30');
  filterTransactions();
}
function deleteTransaction(id) {
  if(!confirm('Delete this transaction?')) return;
  expenses=expenses.filter(e=>e.id!==id); saveUserData(); toast('Transaction deleted.','warning');
  if(currentView==='transactions') filterTransactions();
  else if(currentView==='dashboard') renderDashboard();
}

// ── ADD EXPENSE ──
function renderExpenseView() {
  const dateInp=document.getElementById('exp-date'); if(dateInp&&!dateInp.value) dateInp.value=today();
  renderBudgetRing(); updateBudgetSummary();
  const tips=['The 50/30/20 rule: 50% needs, 30% wants, 20% savings.','Track every expense, even small ones.','Review spending weekly and adjust habits.','Avoid impulse purchases — wait 24 hours before buying.','Meal prepping saves ₹1,500–₹3,000/month.'];
  setText('quick-tip-text',tips[Math.floor(Math.random()*tips.length)]);
}
function updateBudgetSummary() {
  const limit=getDailyLimit(),spent=getTodaySpend(),rem=Math.max(0,limit-spent);
  setText('bsum-spent',fmt(spent));setText('bsum-rem',fmt(rem));setText('bsum-limit',fmt(limit));
  const remEl=document.getElementById('bsum-rem'); if(remEl) remEl.className=rem<0?'red':'green';
}
function selectCat(btn) { document.querySelectorAll('#category-select .cat-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); selectedCat=btn.dataset.cat; }
function selectType(btn) {
  document.querySelectorAll('#expense-form .type-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); selectedType=btn.dataset.type;
  if(selectedType==='credit'){const incBtn=document.querySelector('#category-select [data-cat="Income"]');if(incBtn)selectCat(incBtn);}
}
function initExpenseForm() {
  document.getElementById('expense-form')?.addEventListener('submit',e=>{
    e.preventDefault();
    const amount=parseFloat(document.getElementById('exp-amount').value), note=document.getElementById('exp-note').value.trim(), date=document.getElementById('exp-date').value||today();
    if(!amount||amount<=0){showFieldErr('exp-amount-err','Please enter a valid amount.');return;} clearFieldErr('exp-amount-err');
    const exp={id:uid(),amount,category:selectedCat,note,date,type:selectedType};
    expenses.unshift(exp); saveUserData();
    toast(`${selectedType==='credit'?'Income':'Expense'} of ${fmt(amount)} saved!`,'success');
    document.getElementById('exp-amount').value=''; document.getElementById('exp-note').value='';
    renderBudgetRing(); updateBudgetSummary(); checkBadgesAndAlerts();
  });
}
function checkBadgesAndAlerts() {
  const spent=getTodaySpend(),limit=getDailyLimit();
  if(spent>limit*1.5) toast("You've exceeded 150% of your daily budget!",'error');
  else if(spent>limit) toast("You've exceeded today's budget.",'warning');
  const earned=getEarnedBadges();
  if(earned.length&&expenses.length===1) toast('You earned the "'+earned[0].title+'" badge!','success');
}

// ── ANALYTICS ──
function renderAnalytics() {
  const period=document.getElementById('analytics-period')?.value||'30';
  let list=[...expenses];
  if(period!=='all'){const cutoff=new Date();cutoff.setDate(cutoff.getDate()-parseInt(period));list=list.filter(e=>new Date(e.date+'T00:00:00')>=cutoff);}
  const debits=list.filter(e=>e.type!=='credit'), credits=list.filter(e=>e.type==='credit');
  const totalSpent=debits.reduce((s,e)=>s+e.amount,0), totalInc=credits.reduce((s,e)=>s+e.amount,0);
  const days={}; debits.forEach(e=>{days[e.date]=(days[e.date]||0)+e.amount;});
  const daysArr=Object.values(days), avgDaily=daysArr.length?totalSpent/daysArr.length:0;
  const top=daysArr.length?Math.max(...daysArr):0;
  const sumRow=document.getElementById('analytics-summary-row');
  if(sumRow) sumRow.innerHTML=`
    <div class="card card-stat"><div class="stat-label">Total Spent</div><div class="stat-value" style="color:var(--red)">${fmt(totalSpent)}</div><div class="stat-sub">${debits.length} transactions</div></div>
    <div class="card card-stat"><div class="stat-label">Total Income</div><div class="stat-value" style="color:var(--credit-color)">${fmt(totalInc)}</div><div class="stat-sub">${credits.length} credits</div></div>
    <div class="card card-stat"><div class="stat-label">Avg Daily Spend</div><div class="stat-value">${fmt(Math.round(avgDaily))}</div><div class="stat-sub">vs ${fmt(getDailyLimit())} limit</div></div>
    <div class="card card-stat"><div class="stat-label">Highest Day</div><div class="stat-value">${fmt(top)}</div><div class="stat-sub">Single day peak</div></div>`;
  renderMonthlyTrendChart(list);
  renderAnalyticsCatChart(list);
  renderSmartAnalysis(list,totalSpent,avgDaily);
  renderCatBreakdown(list);
}
function renderMonthlyTrendChart(list) {
  const ctx=document.getElementById('monthlyTrendChart'); if(!ctx) return;
  const months={};
  list.filter(e=>e.type!=='credit').forEach(e=>{const m=e.date.slice(0,7);months[m]=(months[m]||0)+e.amount;});
  const sorted=Object.keys(months).sort();
  const labels=sorted.map(m=>{const d=new Date(m+'-01');return d.toLocaleDateString('en-IN',{month:'short',year:'2-digit'});});
  const data=sorted.map(m=>months[m]);
  if(analyticsChart) analyticsChart.destroy();
  analyticsChart=new Chart(ctx,{type:'bar',data:{labels,datasets:[{label:'Monthly Spend',data,backgroundColor:'rgba(99,102,241,.7)',borderRadius:6,borderSkipped:false}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>'Spent: '+fmt(c.parsed.y)}}},scales:{x:{grid:{display:false},ticks:{font:{family:'Inter',size:10},color:'#94A3B8'}},y:{grid:{color:'#F1F5F9'},ticks:{font:{family:'Inter',size:10},color:'#94A3B8',callback:v=>'₹'+v.toLocaleString('en-IN')},beginAtZero:true}}}});
}
function renderAnalyticsCatChart(list) {
  const ctx=document.getElementById('analyticsCatChart'); if(!ctx) return;
  const cats=getSpendByCategory(list), labels=Object.keys(cats), data=Object.values(cats);
  if(!labels.length){if(analyticsCatChart){analyticsCatChart.destroy();analyticsCatChart=null;}ctx.parentElement.innerHTML=`<p class="empty-state" style="padding:2rem 0">No data yet.</p>`;return;}
  if(analyticsCatChart) analyticsCatChart.destroy();
  analyticsCatChart=new Chart(ctx,{type:'doughnut',data:{labels,datasets:[{data,backgroundColor:COLORS.slice(0,labels.length),borderWidth:2,borderColor:'#fff'}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{font:{family:'Inter',size:10},color:'#475569',padding:8,boxWidth:10}},tooltip:{callbacks:{label:c=>c.label+': '+fmt(c.parsed)}}},cutout:'60%'}});
}
function renderSmartAnalysis(list,totalSpent,avgDaily) {
  const grid=document.getElementById('analysis-grid'),tag=document.getElementById('analysis-health-tag'); if(!grid) return;
  const items=[]; const limit=getDailyLimit();
  if(!list.length){grid.innerHTML=`<p class="empty-state">Add transactions to see insights.</p>`;if(tag){tag.textContent='No Data';tag.className='badge-tag';}return;}
  const cats=getSpendByCategory(list); const topCat=Object.entries(cats).sort((a,b)=>b[1]-a[1])[0];
  if(topCat) items.push({icon:'🏆',type:'',title:'Top Category',text:`Your biggest spend is <strong>${topCat[0]}</strong> at ${fmt(topCat[1])}.`});
  if(avgDaily>limit) items.push({icon:'🚨',type:'danger',title:'Over Daily Average',text:`Your avg daily spend (${fmt(Math.round(avgDaily))}) exceeds your limit (${fmt(limit)}).`});
  else if(avgDaily>limit*0.8) items.push({icon:'⚠️',type:'warning',title:'Near Daily Limit',text:`Avg daily spend of ${fmt(Math.round(avgDaily))} is close to your ${fmt(limit)} limit.`});
  else items.push({icon:'✅',type:'positive',title:'On Track',text:`Great job! Daily avg ${fmt(Math.round(avgDaily))} is within your ${fmt(limit)} budget.`});
  const foodSpent=cats['Food & Dining']||0;
  if(foodSpent>totalSpent*0.4) items.push({icon:'🍽️',type:'warning',title:'High Food Spend',text:`Food & Dining is ${Math.round(foodSpent/totalSpent*100)}% of your total. Consider meal prepping.`});
  const streak=getStreak();
  if(streak>=3) items.push({icon:'🔥',type:'positive',title:`${streak}-Day Streak`,text:`Impressive! You've stayed within budget for ${streak} days in a row.`});
  else if(streak===0) items.push({icon:'💡',type:'',title:'Start a Streak',text:'Try to stay within your daily budget to build a spending streak.'});
  if(totalSpent>0&&getTotalIncome()===0) items.push({icon:'💰',type:'warning',title:'No Income Logged',text:'Log your salary or income to track your net balance accurately.'});
  const health=avgDaily<=limit*0.75?'Healthy':avgDaily<=limit?'Good':avgDaily<=limit*1.2?'Fair':'Poor';
  if(tag){const cls=health==='Healthy'||health==='Good'?'':'warning';tag.textContent=health;tag.className='badge-tag'+(cls?' '+cls:'');}
  grid.innerHTML=items.map(i=>`<div class="analysis-item ${i.type}"><div class="analysis-icon">${i.icon}</div><div class="analysis-text"><strong>${i.title}</strong><span>${i.text}</span></div></div>`).join('');
}
function renderCatBreakdown(list) {
  const el=document.getElementById('cat-breakdown-list'); if(!el) return;
  const cats=getSpendByCategory(list); const total=Object.values(cats).reduce((a,b)=>a+b,0);
  if(!total){el.innerHTML=`<p class="empty-state">No expense data available.</p>`;return;}
  const sorted=Object.entries(cats).sort((a,b)=>b[1]-a[1]);
  el.innerHTML=sorted.map(([cat,amt],i)=>{
    const pct=Math.round(amt/total*100), color=COLORS[i%COLORS.length];
    return `<div class="cat-row"><div class="cat-row-icon">${CAT_ICONS[cat]||'📦'}</div><div class="cat-row-info"><div class="cat-row-name">${cat}</div><div class="cat-row-bar-wrap"><div class="cat-row-bar" style="width:${pct}%;background:${color}"></div></div></div><div class="cat-row-right"><div class="cat-row-amount">${fmt(amt)}</div><div class="cat-row-pct">${pct}%</div></div></div>`;
  }).join('');
}

// ── BUDGET VIEW ──
function renderBudgetView() {
  const bl=budgetLimits, inp=id=>document.getElementById(id);
  if(inp('budget-daily')) inp('budget-daily').value=bl.daily||getDailyLimit();
  ['food','transport','shopping','entertainment','health','bills','edu'].forEach(k=>{if(inp('cb-'+k)) inp('cb-'+k).value=bl[k]||'';});
  renderBudgetProgress();
}
function renderBudgetProgress() {
  const el=document.getElementById('budget-progress-list'); if(!el) return;
  const cats=getSpendByCategory(), bl=budgetLimits;
  const rows=[['Food & Dining','food'],['Transport','transport'],['Shopping','shopping'],['Entertainment','entertainment'],['Health','health']];
  el.innerHTML=rows.filter(([,k])=>bl[k]>0).map(([cat,k])=>{
    const spent=cats[cat]||0, limit=bl[k], pct=Math.round(clamp(spent/limit*100,0,100));
    const color=pct>100?'var(--red)':pct>80?'var(--amber)':'var(--accent)';
    return `<div class="bp-row"><div class="bp-label"><span>${cat}</span><span>${fmt(spent)} / ${fmt(limit)}</span></div><div class="bp-bar"><div class="bp-fill" style="width:${pct}%;background:${color}"></div></div></div>`;
  }).join('')||'<p style="font-size:.82rem;color:var(--muted)">Set category limits above to see progress.</p>';
}
function initBudgetForm() {
  document.getElementById('budget-form')?.addEventListener('submit',e=>{
    e.preventDefault();
    const daily=parseFloat(document.getElementById('budget-daily').value);
    if(!daily||daily<1){toast('Please enter a valid daily limit.','error');return;}
    budgetLimits={daily,food:parseFloat(document.getElementById('cb-food')?.value)||0,transport:parseFloat(document.getElementById('cb-transport')?.value)||0,shopping:parseFloat(document.getElementById('cb-shopping')?.value)||0,entertainment:parseFloat(document.getElementById('cb-entertainment')?.value)||0,health:parseFloat(document.getElementById('cb-health')?.value)||0,bills:parseFloat(document.getElementById('cb-bills')?.value)||0,edu:parseFloat(document.getElementById('cb-edu')?.value)||0};
    currentUser.dailyLimit=daily; saveUserData(); toast('Budget saved successfully.','success');
  });
}

// ── BADGES VIEW ──
function renderBadges() {
  const grid=document.getElementById('badges-grid'); if(!grid) return;
  const earned=getEarnedBadges().map(b=>b.id);
  grid.innerHTML=ALL_BADGES.map(b=>`<div class="badge-card ${earned.includes(b.id)?'earned':'locked'}"><div class="badge-emoji">${b.emoji}</div><div class="badge-title">${b.title}</div><div class="badge-desc">${b.desc}</div><span class="badge-status ${earned.includes(b.id)?'earned':'locked'}">${earned.includes(b.id)?'Earned':'Locked'}</span></div>`).join('');
  renderHistoryTable();
}
function renderHistoryTable() {
  const tbody=document.getElementById('history-body'); if(!tbody) return;
  const limit=getDailyLimit(), days={};
  expenses.filter(e=>e.type!=='credit').forEach(e=>{days[e.date]=(days[e.date]||0)+e.amount;});
  const sorted=Object.entries(days).sort((a,b)=>b[0].localeCompare(a[0])).slice(0,14);
  if(!sorted.length){tbody.innerHTML=`<tr><td colspan="4" style="color:var(--muted);text-align:center;padding:1.5rem">No history yet.</td></tr>`;return;}
  tbody.innerHTML=sorted.map(([date,spent])=>{
    const pct=(spent/limit)*100;
    const status=pct<=75?'<span class="status-pill under">Under Budget</span>':pct<=100?'<span class="status-pill on">On Budget</span>':'<span class="status-pill over">Over Budget</span>';
    return `<tr><td>${fmtDate(date)}</td><td>${fmt(spent)}</td><td>${fmt(limit)}</td><td>${status}</td></tr>`;
  }).join('');
}

// ── PROFILE VIEW ──
function renderProfile() {
  if(!currentUser) return;
  const u=currentUser, init=(u.fname?.[0]||'?').toUpperCase();
  setText('profile-avatar-display',init); document.getElementById('profile-avatar-display').style.background='var(--accent)';
  setText('profile-display-name',(u.fname||'')+' '+(u.lname||'')); setText('profile-display-email',u.email||'');
  const since=u.joinDate?new Date(u.joinDate).toLocaleDateString('en-IN',{month:'long',year:'numeric'}):'Recently';
  setText('member-since-val',since);
  setVal('profile-fname',u.fname||''); setVal('profile-lname',u.lname||''); setVal('profile-email',u.email||''); setVal('profile-phone',u.phone||''); setVal('profile-limit',u.dailyLimit||500);
  const tog=document.getElementById('sms-toggle'); if(tog) tog.classList.toggle('on',autoSmsEnabled);
  const days={};
  expenses.filter(e=>e.type!=='credit').forEach(e=>{days[e.date]=(days[e.date]||0)+e.amount;});
  const limit=getDailyLimit(), onB=Object.values(days).filter(v=>v<=limit).length, overB=Object.values(days).filter(v=>v>limit).length;
  setText('ps-total-exp',expenses.length); setText('ps-on-budget',onB); setText('ps-over-budget',overB);
  setText('ps-streak',getStreak()+' days'); setText('ps-badges',getEarnedBadges().length+'');
  setText('ps-income',fmt(getTotalIncome()));
}
function initProfileForm() {
  document.getElementById('profile-form')?.addEventListener('submit',e=>{
    e.preventDefault();
    currentUser.fname=document.getElementById('profile-fname').value.trim();
    currentUser.lname=document.getElementById('profile-lname').value.trim();
    currentUser.phone=document.getElementById('profile-phone').value.trim();
    const lim=parseFloat(document.getElementById('profile-limit').value);
    if(lim>0){currentUser.dailyLimit=lim;budgetLimits.daily=lim;}
    saveUserData(); updateSidebarUser(); toast('Profile updated.','success'); renderProfile();
  });
}
function clearAllData() {
  if(!confirm('This will permanently delete all your data. Are you sure?')) return;
  if(!confirm('This cannot be undone. Continue?')) return;
  expenses=[]; budgetLimits={daily:currentUser.dailyLimit||500}; saveUserData();
  toast('All data cleared.','warning'); renderProfile();
}

// ── EDIT MODAL ──
function openEditModal(id) {
  const exp=expenses.find(e=>e.id===id); if(!exp) return;
  setVal('edit-txn-id',id); setVal('edit-amount',exp.amount); setVal('edit-note',exp.note||''); setVal('edit-date',exp.date);
  editType=exp.type||'debit'; editCat=exp.category||'Other';
  document.querySelectorAll('#edit-form .type-btn').forEach(b=>{b.classList.toggle('active',b.dataset.type===editType);});
  document.querySelectorAll('#edit-category-select .cat-btn').forEach(b=>{b.classList.toggle('active',b.dataset.cat===editCat);});
  setVal('edit-category',editCat);
  document.getElementById('edit-modal').classList.add('show');
}
function closeEditModal() { document.getElementById('edit-modal').classList.remove('show'); }
function selectEditType(btn) {
  document.querySelectorAll('#edit-form .type-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); editType=btn.dataset.type;
}
function selectEditCat(btn) {
  document.querySelectorAll('#edit-category-select .cat-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); editCat=btn.dataset.cat; setVal('edit-category',editCat);
}
function saveEditedTransaction(e) {
  e.preventDefault();
  const id=document.getElementById('edit-txn-id').value, amount=parseFloat(document.getElementById('edit-amount').value);
  if(!amount||amount<=0){toast('Enter a valid amount.','error');return;}
  const note=document.getElementById('edit-note').value.trim(), date=document.getElementById('edit-date').value||today();
  const idx=expenses.findIndex(e=>e.id===id); if(idx<0) return;
  expenses[idx]={...expenses[idx],amount,category:editCat,note,date,type:editType};
  saveUserData(); closeEditModal(); toast('Transaction updated.','success');
  if(currentView==='dashboard') renderDashboard();
  else if(currentView==='transactions') filterTransactions();
}

// ── SMS PERMISSION MODAL ──
function showSmsPermModal() { document.getElementById('sms-permission-modal').classList.add('show'); }
function closeSmsPermModal() { document.getElementById('sms-permission-modal').classList.remove('show'); DB.set('sms_perm_shown_'+currentUser.email,true); }
function grantSmsPerm() { closeSmsPermModal(); autoSmsEnabled=true; DB.set('sms_'+currentUser.email,true); DB.set('sms_perm_shown_'+currentUser.email,true); const tog=document.getElementById('sms-toggle'); if(tog) tog.classList.add('on'); updateSmsChip(); startSmsSimulator(); toast('SMS auto-detection enabled!','success'); }
function denySmsPerm() { closeSmsPermModal(); toast('You can enable SMS detection anytime from Profile.',''); }

// ── SMS TOGGLE ──
function toggleSmsPermission() {
  autoSmsEnabled=!autoSmsEnabled; DB.set('sms_'+currentUser.email,autoSmsEnabled);
  const el=document.getElementById('sms-toggle'); if(el) el.classList.toggle('on',autoSmsEnabled);
  updateSmsChip();
  if(autoSmsEnabled){toast('SMS auto-detection enabled.','success');startSmsSimulator();}
  else{toast('SMS auto-detection disabled.','warning');stopSmsSimulator();}
}
function startSmsSimulator() {
  stopSmsSimulator();
  function trigger() { if(!autoSmsEnabled) return; fireRandomSms(); smsTimer=setTimeout(trigger,Math.floor(Math.random()*9000)+6000); }
  smsTimer=setTimeout(trigger,Math.floor(Math.random()*7000)+4000);
}
function stopSmsSimulator() { if(smsTimer) clearTimeout(smsTimer); smsTimer=null; }
function fireRandomSms() {
  if(document.getElementById('app-shell').classList.contains('hidden')) return;
  if(document.getElementById('sms-modal').classList.contains('show')) return;
  const msg=FAKE_SMS[Math.floor(Math.random()*FAKE_SMS.length)], parsed=parseSms(msg);
  if(parsed&&parsed.amount) showSmsModal(msg,parsed);
}
function showSmsModal(rawMsg,parsed) {
  document.getElementById('sms-modal-msg').textContent=rawMsg;
  setVal('sms-modal-amount',parsed.amount);
  setVal('sms-modal-note-input',parsed.merchant||'');
  setVal('sms-modal-txn-type',parsed.type||'debit');
  const typeDisp=document.getElementById('sms-modal-type-display');
  if(typeDisp){typeDisp.textContent=parsed.type==='credit'?'Credit':'Debit';typeDisp.className='type-badge '+(parsed.type==='credit'?'credit':'debit');}
  document.querySelectorAll('.cat-modal-grid .cat-btn').forEach(b=>{b.classList.remove('active');if(b.dataset.cat===parsed.category)b.classList.add('active');});
  setVal('sms-modal-raw-cat',parsed.category||'Other');
  document.getElementById('sms-modal').classList.add('show');
}
function closeSmsModal() { document.getElementById('sms-modal').classList.remove('show'); }
function setSmsModalCat(btn) { document.querySelectorAll('.cat-modal-grid .cat-btn').forEach(b=>b.classList.remove('active')); btn.classList.add('active'); setVal('sms-modal-raw-cat',btn.dataset.cat); }
function saveSmsModalExpense(e) {
  e.preventDefault();
  const amount=parseFloat(document.getElementById('sms-modal-amount').value), cat=document.getElementById('sms-modal-raw-cat').value;
  const note=document.getElementById('sms-modal-note-input').value.trim()||'SMS Auto-detected', type=document.getElementById('sms-modal-txn-type').value||'debit';
  if(!amount||amount<=0){toast('Invalid amount.','error');return;}
  const exp={id:uid(),amount,category:cat,note,date:today(),type,source:'sms'};
  expenses.unshift(exp); saveUserData();
  toast(`Auto-saved ${type==='credit'?'income':'expense'} of ${fmt(amount)}.`,'success');
  closeSmsModal();
  if(currentView==='dashboard') renderDashboard();
  else if(currentView==='transactions') filterTransactions();
  else if(currentView==='expenses') renderExpenseView();
  checkBadgesAndAlerts();
}

// ── TOAST ──
function toast(msg,type='') {
  const icons={success:`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,warning:`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,error:`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`};
  const container=document.getElementById('toast-container'); if(!container) return;
  const el=document.createElement('div'); el.className=`toast ${type}`;
  el.innerHTML=`<span class="toast-icon">${icons[type]||'ℹ️'}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(()=>{el.style.opacity='0';el.style.transform='translateY(8px)';el.style.transition='.3s';setTimeout(()=>el.remove(),320);},3200);
}

// ── BOOTSTRAP ──
document.addEventListener('DOMContentLoaded',()=>{
  initAuth(); initExpenseForm(); initBudgetForm(); initProfileForm(); checkSession();
  document.getElementById('edit-modal')?.addEventListener('click',e=>{if(e.target===e.currentTarget)closeEditModal();});
  document.getElementById('sms-modal')?.addEventListener('click',e=>{if(e.target===e.currentTarget)closeSmsModal();});
  document.getElementById('sms-permission-modal')?.addEventListener('click',e=>{if(e.target===e.currentTarget)closeSmsPermModal();});
});
