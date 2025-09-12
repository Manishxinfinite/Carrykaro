document.addEventListener('DOMContentLoaded', function(){
  const genBtn = document.getElementById('generateCoupon');
  if(genBtn){
    genBtn.addEventListener('click', async ()=>{
      genBtn.disabled = true;
      genBtn.textContent = 'Generating...';
      try{
        const res = await fetch('/generate_coupon', { method: 'POST', headers:{'Content-Type':'application/json'} });
        const data = await res.json();
        const area = document.getElementById('couponArea');
        area.innerHTML = `
          <div class="card p-3 text-center">
            <h5>${data.code}</h5>
            <p>${data.discount}% off</p>
            <img src="${data.qr}" alt="QR">
            <p class="small text-muted mt-2">Scan the QR to view coupon. Waiting for approval.</p>
          </div>`;
      }catch(e){
        alert('Failed to generate');
      }finally{genBtn.disabled=false;genBtn.textContent='Get Coupon (Generate QR)'}
    });
  }

  // Approve / Reject handlers
  document.querySelectorAll('.approveBtn').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const code = btn.dataset.code;
      if(!confirm('Approve coupon '+code+'?')) return;
      btn.disabled = true;
      const res = await fetch('/approve_coupon', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code})});
      const j = await res.json();
      if(j.ok) location.reload(); else alert('Error');
    });
  });
  document.querySelectorAll('.rejectBtn').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const code = btn.dataset.code;
      if(!confirm('Reject coupon '+code+'?')) return;
      btn.disabled = true;
      const res = await fetch('/reject_coupon', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({code})});
      const j = await res.json();
      if(j.ok) location.reload(); else alert('Error');
    });
  });
});
