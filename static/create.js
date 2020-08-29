function readURL(input) {
  if (input.files && input.files[0]) {
    var reader = new FileReader();
    
    var extension = input.files[0].name.split('.').pop().toLowerCase();
    console.log(extension);
    if (extension == 'mp4'){
	    reader.onload = function(e){
		    $('#videoPreview').attr('src', e.target.result);
	    }
	    reader.readAsDataURL(input.files[0]); // convert to base64 string
	    
	    $('#imgPreview').hide();
	    $('#videoPreview').show();
    }else{
	    reader.onload = function(e) {
	      $('#imgPreview').attr('src', e.target.result);
	    }
	    
	    reader.readAsDataURL(input.files[0]); // convert to base64 string
	    $('#videoPreview').hide();
	    $('#imgPreview').show();
    }
  }
  else {
	  $('#imgPreview').hide();
  }
}

function previewLink(){
	var clipSlug = $('#linkInput').val();
	if (clipSlug != ''){
		link = 'https://clips.twitch.tv/embed?clip='+clipSlug+'&parent=gameshots.gg&parent=ec2-54-188-110-37.us-west-2.compute.amazonaws.com';
		$('#twitchPreview').attr('src', link);	
		$('#twitchPreview').show();
	}
	else{
		$('#twitchPreview').hide();
	}
	
}

function previewYoutubeLink(){
	var clipSlug = $('#youtubeLinkInput').val();
	if (clipSlug != ''){
		link = 'https://www.youtube.com/embed/'+clipSlug+'?&autoplay=1'
		$('#youtubePreview').attr('src', link);	
		$('#youtubePreview').show();
	}else{
		$('#youtubePreview').hide();
	}
}

function addTag(){
	var tagList = $('#tagList');
	var len = $('#tagList li').length;
	var newInput = $('<input type="text" name="tag'+(len).toString()+'" class="tag"/>');
	var newTag = $('<li>');
	
	newInput.autocomplete({
                source: autoCompleteTags,
                minLength: 3,
                select: function(event, ui){
                        console.log('selected:'+ui.item.value);
                }
        });
	newTag.append(newInput);

	tagList.append(newTag);
}

function autoCompleteTags(request, response){
			$.ajax({
				url: "/autocompleteTag",
				dataType: "json",
				data: {
					term: request.term
				},
				success: function(data){
					response(data);
				}
			});
}

function showTwitchInput(){
	$('.shotDiv').hide();
	$('#youtubePreview').attr('src', '');	
	$('#videoPreview').trigger('pause');
	$('#twitchLinkDiv').show();
	var clipSlug = $('#linkInput').val();
	if (clipSlug != ''){
		link = 'https://clips.twitch.tv/embed?clip='+clipSlug+'&parent=gameshots.gg&parent=ec2-54-188-110-37.us-west-2.compute.amazonaws.com';
		$('#twitchPreview').attr('src', link);	
	}
}

function showMediaInput(){
	$('.shotDiv').hide();
	$('#youtubePreview').attr('src', '');	
	$('#twitchPreview').attr('src', '');	
	$('#mediaDiv').show();
}

function showYoutubeInput(){
	$('.shotDiv').hide();
	$('#twitchPreview').attr('src', '');	
	$('#videoPreview').trigger('pause');
	$('#youtubeLinkDiv').show();
	var clipSlug = $('#youtubeLinkInput').val();
	if (clipSlug != ''){
		link = 'https://www.youtube.com/embed/'+clipSlug+'?&autoplay=1'
		$('#youtubePreview').attr('src', link);	
	}
}

window.onload = function(){
	$("#imgInput").change(function() {
	  readURL(this);
	});

	$("#linkInput").change(function() {
		previewLink();
	});

	$("#youtubeLinkInput").change(function() {
		previewYoutubeLink();
	});

	$('#game').autocomplete({
		source: function (request, response){
			$.ajax({
				url: "/autocompleteGames",
				dataType: "json",
				data: {
					term: request.term
				},
				success: function(data){
					response(data);
				}
			});

		},
		minLength: 2,
		select: function(event, ui){
			console.log('selected:'+ui.item.value);
		}
	});

	$('.tag').autocomplete({
		source: autoCompleteTags,
		minLength: 3,
		select: function(event, ui){
			console.log('selected:'+ui.item.value);
		}
	});
};
