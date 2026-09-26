const configuredApi=localStorage.getItem("API_URL");
const API=(configuredApi||((location.protocol==="http:"||location.protocol==="https:")?location.origin:"http://127.0.0.1:8000")).replace(/\/$/,"");
const $=s=>document.querySelector(s),list=$("#flightList"),status=$("#status");
function esc(v){return String(v??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;")}
function money(n){return "₹"+Number(n||0).toLocaleString("en-IN",{maximumFractionDigits:0})}
function showStatus(msg,error=false){status.textContent=msg;status.style.color=error?"#b42318":"#667085"}
async function getFlights(params={}){const q=new URLSearchParams();Object.entries(params).forEach(([k,v])=>v&&q.set(k,v));const r=await fetch(API+"/flights"+(q.toString()?"?"+q:""));if(!r.ok)throw new Error((await r.json().catch(()=>({}))).detail||"Unable to load flights");return r.json()}
function renderFlights(fs){if(!fs.length){list.innerHTML='<div class="status">No flights found.</div>';return}list.innerHTML=fs.map(f=>'<article class="flight-card"><div><div class="airline">'+esc(f.airline)+'</div><div class="flight-number">'+esc(f.flight_number)+'</div></div><div><div class="route">'+esc(f.source)+' <span>→</span> '+esc(f.destination)+'</div><div class="flight-number">'+esc(new Date(f.departure_time).toLocaleString())+' · '+f.duration_minutes+' min · '+f.available_seats+' seats left</div></div><div class="fare"><strong>'+money(f.dynamic_price)+'</strong><span class="tier">'+esc(f.pricing_tier)+'</span></div><button class="primary-btn book-btn" data-flight-id="'+f.flight_id+'" data-flight-name="'+esc(f.airline+" "+f.flight_number)+'" data-price="'+f.dynamic_price+'">Book</button></article>').join("")}
async function loadFlights(){try{showStatus("Loading live fares…");renderFlights(await getFlights());showStatus("Fares calculated from current seat, demand and departure data.")}catch(e){showStatus(e.message+" — make sure FastAPI is running.",true);list.innerHTML=""}}
$("#searchForm").addEventListener("submit",async e=>{e.preventDefault();try{showStatus("Searching…");renderFlights(await getFlights({origin:$("#origin").value.trim(),destination:$("#destination").value.trim(),date:$("#date").value}));showStatus("Search complete.")}catch(e){showStatus(e.message,true);list.innerHTML=""}});
$("#sort").addEventListener("change",async()=>{try{renderFlights(await getFlights({sort_by:$("#sort").value}))}catch(e){showStatus(e.message,true)}});
$("#refreshBtn").onclick=loadFlights;
list.addEventListener("click",e=>{const btn=e.target.closest(".book-btn");if(!btn)return;openBooking(Number(btn.dataset.flightId),btn.dataset.flightName,Number(btn.dataset.price));});
function openBooking(id,name,price){$("#bookingForm").reset();$("#flightId").value=id;$("#modalFlight").textContent=name+" · "+money(price)+" / seat";$("#bookingStatus").textContent="";$("#modal").classList.remove("hidden")}
$("#closeModal").onclick=()=>$("#modal").classList.add("hidden");
$("#modal").addEventListener("click",e=>{if(e.target.id==="modal")$("#modal").classList.add("hidden")});
$("#bookingForm").addEventListener("submit",async e=>{e.preventDefault();const out=$("#bookingStatus");out.textContent="Processing simulated payment…";const body={flight_id:Number($("#flightId").value),passenger_name:$("#passengerName").value,passenger_email:$("#passengerEmail").value||null,passenger_phone:$("#passengerPhone").value||null,seat_number:$("#seatNumber").value||null,force_payment_success:true};try{const r=await fetch(API+"/db/booking",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),data=await r.json();if(!r.ok)throw new Error(data.detail||"Booking failed");out.textContent="Booking confirmed. PNR: "+data.pnr;out.style.color="#087443";loadFlights();loadBookings()}catch(err){out.textContent=err.message;out.style.color="#b42318"}});
async function loadBookings(){const box=$("#bookingList");box.innerHTML='<div class="status">Loading…</div>';try{const r=await fetch(API+"/db/bookings");if(!r.ok)throw new Error("Could not load bookings");const data=await r.json();box.innerHTML=data.length?data.map(b=>'<div class="booking-card"><div><b>PNR '+esc(b.pnr)+'</b><div class="muted">Flight #'+b.flight_id+' · Seat '+esc(b.seat_number||"—")+' · '+esc(new Date(b.booking_date).toLocaleString())+'</div></div><div><b>'+money(b.total_price)+'</b><div class="confirmed">'+esc(b.status)+'</div>'+(b.status==="Confirmed"?'<button class="ghost-btn cancel-btn" data-pnr="'+esc(b.pnr)+'">Cancel</button>':'')+'</div></div>').join(""):'<div class="status">No bookings yet.</div>'}catch(e){box.innerHTML='<div class="status">'+e.message+'</div>'}}
$("#bookingList").addEventListener("click",async e=>{
  const btn=e.target.closest(".cancel-btn");
  if(!btn)return;
  if(!confirm("Cancel booking "+btn.dataset.pnr+"?"))return;
  try{
    const r=await fetch(API+"/db/booking/"+encodeURIComponent(btn.dataset.pnr),{method:"DELETE"});
    const data=await r.json().catch(()=>({}));
    if(!r.ok)throw new Error(data.detail||"Cancellation failed");
    await loadBookings();
    await loadFlights();
  }catch(err){
    alert(err.message);
  }
});
$("#loadBookings").onclick=loadBookings;loadFlights();