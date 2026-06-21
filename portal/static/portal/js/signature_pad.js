function initSignaturePad(canvasId, hiddenInputId, clearBtnId) {
  var canvas = document.getElementById(canvasId);
  var hidden = document.getElementById(hiddenInputId);
  if (!canvas || !hidden) return;

  var ctx = canvas.getContext('2d');
  var drawing = false;
  var hasDrawn = false;

  ctx.lineWidth = 2.2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#14213D';

  function pos(evt) {
    var rect = canvas.getBoundingClientRect();
    var point = evt.touches ? evt.touches[0] : evt;
    return {
      x: (point.clientX - rect.left) * (canvas.width / rect.width),
      y: (point.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  function start(evt) {
    evt.preventDefault();
    drawing = true;
    hasDrawn = true;
    var p = pos(evt);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
  }

  function move(evt) {
    if (!drawing) return;
    evt.preventDefault();
    var p = pos(evt);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
  }

  function end() {
    drawing = false;
  }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);
  canvas.addEventListener('touchstart', start, { passive: false });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);

  var clearBtn = clearBtnId && document.getElementById(clearBtnId);
  if (clearBtn) {
    clearBtn.addEventListener('click', function (evt) {
      evt.preventDefault();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      hasDrawn = false;
      hidden.value = '';
    });
  }

  var form = canvas.closest('form');
  if (form) {
    form.addEventListener('submit', function () {
      hidden.value = hasDrawn ? canvas.toDataURL('image/png') : '';
    });
  }
}
