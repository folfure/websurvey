var socket = null;

var logBox = null;

	logBox = document.getElementById('log_window');

if (!Date.now)
{
    Date.now = function() { return new Date().getTime(); }
}


function addToLog(log)
{
  // alert("send");
  if (logBox == null )
  {
  	logBox = document.getElementById('log_window');
  }
  logBox.innerHTML = log + '<br/>' + logBox.innerHTML;
  // Large enough to keep showing the latest message.
  //logBox.scrollTop = 1000000;
}

