var newNotifications = 0;
var since = 0;

function longPoll() {
        var shouldDelay = false;

        $.ajax({
            url: '/getNotifications?since='+since,
            async: true,            // by default, it's async, but...
            dataType: 'json',       // or the dataType you are working with
            timeout: 10000,          // IMPORTANT! this is a 10 seconds timeout
            cache: false

        }).done(function (data, textStatus, jqXHR) {
             // do something with data...
	    if (data.length > 0){
		    for (notification in data){
			addNotification(notification);		
		    }
		    updateNotificationCount(data.length+newNotifications);
		    since = data[data.length-1][4];
 	    }
	   

        }).fail(function (jqXHR, textStatus, errorThrown ) {
            shouldDelay = textStatus !== "timeout";

        }).always(function() {
            // in case of network error. throttle otherwise we DOS ourselves. If it was a timeout, its normal operation. go again.
            var delay = shouldDelay ? 30000: 10000;
            window.setTimeout(longPoll, delay);
        });
}

function addNotification(notification){

}

function updateNotificationCount(x){
	newNotifications = x;
	if (x > 0){
		$("#notificationBell").addClass('badge-danger');
	} else {
		$("#notificationBell").removeClass('badge-danger');
	}
	$("#notificationCount").text(x);
}

window.onload = function(){
	if (username != null){
		longPoll(); //fire first handler
	}
	$('#notificationButton').on('click', function(e){
		updateNotificationCount(0);
	});
}
