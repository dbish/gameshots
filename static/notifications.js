var newNotifications = [];
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
		    console.log(data);
		    for (i in data){
			addNotification(data[i]);		
		    }
		    console.log(newNotifications);
		    updateNotificationCount(newNotifications.length);
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
	console.log(notification);
	if (notification[5] == 0){
		$('#notificationList').append(
			$('<li>').
			addClass('unreadNotification').append(
				$('<a>').attr('href', notification[2]).append(notification[3])));
		newNotifications.push(notification[0]);
	}else {
		$('#notificationList').append(
			$('<li>').append(
				$('<a>').attr('href', notification[2]).append(notification[3])));
	}

}

function markNotificationsRead(){
	$.post('/markNotificationsRead',{
                'notifications':JSON.stringify(newNotifications),
        }).done(function(response){
		console.log('done clearing');
        }).fail(function(){
                console.log('could not clear notifications');
        });

}

function updateNotificationCount(x){
	if (x > 0){
		$("#notificationBell").addClass('badge-danger');
	} else {
		$("#notificationBell").removeClass('badge-danger');
		if (newNotifications.length > 0){
			markNotificationsRead();
			newNotifications = [];
		}
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
	 $(function(){
	    $("[data-toggle=popover]").popover({
		html : true,
		content: function() {
		  var content = $(this).attr("data-popover-content");
		  return $(content).children(".popover-body").html();
		},
		title: function() {
		  var title = $(this).attr("data-popover-content");
		  return $(title).children(".popover-heading").html();
		}
	    });
	 });
}
