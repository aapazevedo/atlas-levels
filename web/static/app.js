const $ = (id) => document.getElementById(id);

let token = null;
let role = null;
let lastLevels = null;

function setStatus(el, msg, ok=true){
  el.textContent = msg;
  el.className = "status " + (ok ? "ok" : "bad");
}

function todayISO(){
  const d = new Date();
  const pad = (n)=> String(n).padStart(2,"0");
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
}

$("validFor").value = todayISO();
$("a_validfor").value = todayISO();
$("a_tradedate").value = todayISO();

async function api(path, opts={}){
  const headers = opts.headers || {};
  if(token) headers["Authorization"] = `Bearer ${token}`;
  if(opts.json) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
    delete opts.json;
  }
  opts.headers = headers;

  const res = await fetch(path, opts);
  const txt = await res.text();
  let data = null;
  try { data = JSON.parse(txt); } catch { data = txt; }

  if(!res.ok) throw {status: res.status, data};
  return data;
}

async function refreshSymbols(){
  const sel = $("symbol");
  sel.innerHTML = "";
  const data = await api("/api/symbols");
  (data.symbols || []).forEach(s=>{
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    sel.appendChild(opt);
  });
}

function formatLevels(obj){
  const l = obj.levels;
  return [
    `symbol: ${obj.symbol}`,
    `valid_for: ${obj.valid_for}`,
    obj.trade_date ? `trade_date: ${obj.trade_date}` : ``,
    "",
    `VAH: ${l.vah}`,
    `VAL: ${l.val}`,
    `LVN: ${(l.lvn && l.lvn.length) ? l.lvn[0] : ""}`,
    `Institutional Buy: ${l.institutional_buy}`,
    `Institutional Sell: ${l.institutional_sell}`
  ].filter(Boolean).join("\n");
}

function download(filename, content, mime){
  const blob = new Blob([content], {type: mime});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

// =====================
// LOGIN / LOGOUT
// =====================
$("loginBtn").onclick = async ()=>{
  try{
    const data = await api("/api/auth/login", {
      method: "POST",
      json: {
        email: $("email").value.trim(),
        password: $("password").value
      }
    });

    token = data.access_token;
    role = data.role;

    $("whoami").textContent = `${data.email} (${data.role})`;
    $("logoutBtn").style.display = "inline-block";
    setStatus($("loginStatus"), "Login OK", true);

    await refreshSymbols();
    $("adminCard").style.display = (role === "admin") ? "block" : "none";

    if(role === "admin"){
      await loadUsers();
    }

  }catch(e){
    setStatus($("loginStatus"), "Falha no login", false);
  }
};

$("logoutBtn").onclick = ()=>{
  token = null; role = null; lastLevels = null;
  $("whoami").textContent = "Deslogado";
  $("logoutBtn").style.display = "none";
  $("levelsBox").textContent = "Faça login e carregue um ativo.";
  $("adminCard").style.display = "none";
};

// =====================
// NÍVEIS
// =====================
$("loadBtn").onclick = async ()=>{
  try{
    const sym = $("symbol").value;
    const validFor = $("validFor").value;
    const q = new URLSearchParams({symbol: sym, valid_for: validFor});
    const data = await api(`/api/levels?${q.toString()}`);
    lastLevels = data;
$("k_symbol").textContent = data.symbol;
$("k_date").textContent = data.valid_for;
    $("levelsBox").textContent = formatLevels(data);
    $("copyBtn").disabled = false;
    $("csvBtn").disabled = false;
    $("jsonBtn").disabled = false;
  }catch{
    $("levelsBox").textContent = "Níveis não encontrados.";
  }
};

$("copyBtn").onclick = async ()=>{
  if(!lastLevels) return;
  await navigator.clipboard.writeText(formatLevels(lastLevels));
};

$("jsonBtn").onclick = ()=>{
  if(!lastLevels) return;
  download(`${lastLevels.symbol}_${lastLevels.valid_for}.json`, JSON.stringify(lastLevels, null, 2), "application/json");
};

$("csvBtn").onclick = ()=>{
  if(!lastLevels) return;
  const l = lastLevels.levels;
  const csv = [
    "symbol,valid_for,trade_date,vah,val,lvn1,inst_buy,inst_sell",
    [
      lastLevels.symbol,
      lastLevels.valid_for,
      lastLevels.trade_date || "",
      l.vah,
      l.val,
      (l.lvn && l.lvn.length) ? l.lvn[0] : "",
      l.institutional_buy,
      l.institutional_sell
    ].join(",")
  ].join("\n");
  download(`${lastLevels.symbol}_${lastLevels.valid_for}.csv`, csv, "text/csv");
};

// =====================
// ADMIN - SALVAR MANUAL
// =====================
$("a_save").onclick = async ()=>{
  try{
    await api("/api/admin/levels", {
      method: "POST",
      json: {
        symbol: $("a_symbol").value,
        valid_for: $("a_validfor").value,
        trade_date: $("a_tradedate").value,
        vah: parseFloat($("a_vah").value),
        val: parseFloat($("a_val").value),
        lvn1: ($("a_lvn1").value.trim() ? parseFloat($("a_lvn1").value) : null),
        inst_buy: parseFloat($("a_ib").value),
        inst_sell: parseFloat($("a_is").value)
      }
    });
    setStatus($("adminStatus"), "Salvo com sucesso.", true);
  }catch{
    setStatus($("adminStatus"), "Erro ao salvar.", false);
  }
};

// =====================
// ADMIN - IMPORTAR CSV
// =====================
$("importBtn").onclick = async ()=>{
  if(role !== "admin") return;

  const file = $("csvFile").files?.[0];
  if(!file){
    setStatus($("importStatus"), "Selecione um CSV.", false);
    return;
  }

  const form = new FormData();
  form.append("file", file);

  try{
    const res = await fetch("/api/admin/import_csv", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` },
      body: form
    });

    const data = await res.json();
    if(!res.ok) throw data;

    setStatus($("importStatus"), `OK! Inseridos: ${data.inserted}, Atualizados: ${data.updated}`, true);
  }catch{
    setStatus($("importStatus"), "Erro ao importar CSV.", false);
  }
};

// =====================
// ADMIN - USUÁRIOS
// =====================
$("u_create").onclick = async ()=>{
  try{
    const email = $("u_email").value.trim();
    const password = $("u_pass").value;
    const plan = $("u_plan").value;
    const r = $("u_role").value;

    if(!email || !password){
      setStatus($("userStatus"), "Informe email e senha.", false);
      return;
    }

    await api("/api/admin/users", {
      method: "POST",
      json: { email, password, plan, role: r }
    });

    $("u_email").value = "";
    $("u_pass").value = "";
    setStatus($("userStatus"), "Usuário criado!", true);
    await loadUsers();

  }catch(e){
    setStatus($("userStatus"), "Erro ao criar (email já existe?).", false);
  }
};

$("u_reload").onclick = async ()=>{
  await loadUsers();
};

async function loadUsers(){
  try{
    const data = await api("/api/admin/users");
    renderUsers(data.users || []);
    setStatus($("userStatus"), `Carregado: ${(data.users||[]).length} usuários`, true);
  }catch{
    setStatus($("userStatus"), "Erro ao carregar usuários.", false);
  }
}

function renderUsers(users){
  let html = `<table style="width:100%;border-collapse:collapse;font-size:12px;">
    <thead>
      <tr style="text-align:left;">
        <th style="padding:6px;border-bottom:1px solid #263355;">ID</th>
        <th style="padding:6px;border-bottom:1px solid #263355;">Email</th>
        <th style="padding:6px;border-bottom:1px solid #263355;">Role</th>
        <th style="padding:6px;border-bottom:1px solid #263355;">Plan</th>
        <th style="padding:6px;border-bottom:1px solid #263355;">Nova senha</th>
        <th style="padding:6px;border-bottom:1px solid #263355;">Ação</th>
      </tr>
    </thead><tbody>`;

  for(const u of users){
    html += `<tr>
      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">${u.id}</td>
      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">${u.email}</td>

      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">
        <select id="role_${u.id}" class="input" style="height:28px;padding:4px;">
          <option value="user" ${u.role==="user"?"selected":""}>user</option>
          <option value="admin" ${u.role==="admin"?"selected":""}>admin</option>
        </select>
      </td>

      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">
        <select id="plan_${u.id}" class="input" style="height:28px;padding:4px;">
          <option value="brasil" ${u.plan==="brasil"?"selected":""}>brasil</option>
          <option value="global" ${u.plan==="global"?"selected":""}>global</option>
          <option value="pro" ${u.plan==="pro"?"selected":""}>pro</option>
        </select>
      </td>

      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">
        <input id="pass_${u.id}" class="input" placeholder="(opcional)" type="password" style="height:28px;padding:4px;">
      </td>

      <td style="padding:6px;border-bottom:1px solid #1e2a4a;">
        <button class="btn secondary" onclick="saveUser(${u.id})">Salvar</button>
      </td>
    </tr>`;
  }

  html += `</tbody></table>`;
  $("usersBox").innerHTML = html;
}

window.saveUser = async function(userId){
  try{
    const roleV = $(`role_${userId}`).value;
    const planV = $(`plan_${userId}`).value;
    const passV = $(`pass_${userId}`).value;

    const body = { role: roleV, plan: planV };
    if(passV && passV.trim()){
      body.new_password = passV.trim();
    }

    await api(`/api/admin/users/${userId}`, {
      method: "PATCH",
      json: body
    });

    setStatus($("userStatus"), `Usuário ${userId} atualizado.`, true);
    await loadUsers();
  }catch(e){
    setStatus($("userStatus"), `Erro ao atualizar usuário ${userId}.`, false);
  }
};
