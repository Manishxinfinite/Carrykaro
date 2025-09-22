document.addEventListener('DOMContentLoaded', function(){
  // Coupon generation for user dashboard
  const genBtn = document.getElementById('generateCoupon');
  if(genBtn){
    genBtn.addEventListener('click', async ()=>{
      genBtn.disabled = true;
      genBtn.textContent = 'Generating...';
      try{
        const res = await fetch('/generate_coupon', { 
          method: 'POST', 
          headers:{'Content-Type':'application/json'} 
        });
        const data = await res.json();
        const area = document.getElementById('couponArea');
        
        if (res.ok) {
          area.innerHTML = `
            <div class="card p-3 text-center border-success">
              <h5 class="text-success">Coupon Generated!</h5>
              <p><strong>Code:</strong> ${data.code}</p>
              <p><strong>Discount:</strong> ${data.discount}% off</p>
              <p class="small text-muted mt-2">Your coupon is pending approval from vendor/sponsor.</p>
            </div>`;
        } else {
          area.innerHTML = `
            <div class="card p-3 text-center border-warning">
              <h6 class="text-warning">Cannot Generate Coupon</h6>
              <p class="text-danger">${data.error}</p>
              ${data.next_allowed ? `<p><strong>Next allowed:</strong> ${data.next_allowed}</p>` : ''}
            </div>`;
        }
      } catch(e) {
        const area = document.getElementById('couponArea');
        area.innerHTML = '<div class="alert alert-danger">Failed to generate coupon. Please try again.</div>';
      } finally {
        genBtn.disabled = false;
        genBtn.textContent = 'Get Coupon';
      }
    });
  }

  // Approve button handlers for vendor/sponsor/admin
  document.querySelectorAll('.approveBtn').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const code = btn.dataset.code;
      if(!confirm('Approve coupon '+code+'?')) return;
      
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Approving...';
      
      try {
        const res = await fetch('/approve_coupon', {
          method:'POST', 
          headers:{'Content-Type':'application/json'}, 
          body: JSON.stringify({code})
        });
        const j = await res.json();
        
        if(j.ok) {
          btn.textContent = 'Approved';
          btn.classList.remove('btn-success');
          btn.classList.add('btn-outline-success');
          setTimeout(() => location.reload(), 1000);
        } else {
          alert('Error approving coupon: ' + (j.error || 'Unknown error'));
          btn.disabled = false;
          btn.textContent = originalText;
        }
      } catch (e) {
        alert('Network error. Please try again.');
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  });

  // Reject button handlers for vendor/sponsor/admin
  document.querySelectorAll('.rejectBtn').forEach(btn=>{
    btn.addEventListener('click', async ()=>{
      const code = btn.dataset.code;
      if(!confirm('Reject coupon '+code+'?')) return;
      
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Rejecting...';
      
      try {
        const res = await fetch('/reject_coupon', {
          method:'POST', 
          headers:{'Content-Type':'application/json'}, 
          body: JSON.stringify({code})
        });
        const j = await res.json();
        
        if(j.ok) {
          btn.textContent = 'Rejected';
          btn.classList.remove('btn-danger');
          btn.classList.add('btn-outline-danger');
          setTimeout(() => location.reload(), 1000);
        } else {
          alert('Error rejecting coupon: ' + (j.error || 'Unknown error'));
          btn.disabled = false;
          btn.textContent = originalText;
        }
      } catch (e) {
        alert('Network error. Please try again.');
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  });
});