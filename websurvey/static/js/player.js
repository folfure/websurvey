
var user_id = null;
var team = null;
var need_reconnect = false;

function connect_player()
{if (!('WebSocket' in window))
	{
		addToLog('WebSocket is not available');
	}

	var scheme = window.location.protocol == 'https:' ? 'wss://' : 'ws://';
	var defaultAddress = scheme + window.location.host + '/buzz';
	var url = defaultAddress+'?user='+player; 			//addressBox.value;
	addToLog("Connecting to: "+url);

	if ('WebSocket' in window) {
		socket = new WebSocket(url);
	} else {
		return;
	}

	socket.onopen = function () {
		var extraInfo = [];
		if (('protocol' in socket) && socket.protocol) {
			extraInfo.push('protocol = ' + socket.protocol);
		}
		if (('extensions' in socket) && socket.extensions) {
			extraInfo.push('extensions = ' + socket.extensions);
		}

		var logMessage = 'Opened';
		if (extraInfo.length > 0) {
			logMessage += ' (' + extraInfo.join(', ') + ')';
		}
		addToLog(logMessage);
	};
	socket.onmessage = function (event) {
		var obj = JSON.parse(event.data);
		if (obj.type=='question')
		{
			addToLog('< ' + (obj.question )+' ' +obj.answers);
		}

	};
	socket.onerror = function () {
		addToLog('Error');
	};
	socket.onclose = function (event) {
		var logMessage = 'Closed (';
		if ((arguments.length == 1) && ('CloseEvent' in window) &&
		(event instanceof CloseEvent)) {
		logMessage += 'wasClean = ' + event.wasClean;
		// code and reason are present only for
		// draft-ietf-hybi-thewebsocketprotocol-06 and later
		if ('code' in event) {
		logMessage += ', code = ' + event.code;
		}
		if ('reason' in event) {
		logMessage += ', reason = ' + event.reason;
		}
		} else {
		logMessage += 'CloseEvent is not available';
		}
		addToLog(logMessage + ')');
		need_reconnect=true;
	};
}


function validateSurname()
{
	if ($("#surname").val() != "" && $("team").val() != "")
	{
		player = $("#surname").val();
		team = $("#team :selected").text();
		$.ajax({
		  type: "get",
		  url: "game",
		  data: {player : player, team:team, req_type:"register_user"},
		  cache: false,
		  success: function(data){
		    alert(data);
		  	user_id = data["id"];
		    alert(user_id);
		  }
		});
	}
}


function answer(question, response)
{
	if (need_reconnect==true)
	{
		location.reload();
		return;
		connect_player();
		need_reconnect = false;
		if (!socket)
		{
			addToLog('Not connected');
			return;
		}
	}

  	socket.send(JSON.stringify({
  		type :'answer',
  		from : player,
  		when : Date.now(),
        answer: response,
        question: question
}));
}

$(function(){
	connect_player();
});