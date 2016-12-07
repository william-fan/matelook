#!/usr/bin/perl -w

# written by William Fan October 2016
# http://cgi.cse.unsw.edu.au/~cs2041/assignments/matelook/

use CGI qw/:all/;
use CGI::Carp qw/fatalsToBrowser warningsToBrowser/;
use CGI::Session;
use CGI::Cookie;
use Date::Parse;
use POSIX 'strftime';
use File::Copy;
use File::Path;

sub main() {
    # create session id
    session();

    # print start of HTML ASAP to assist debugging if there is an error in the script
    print page_header();
    
    # Now tell CGI::Carp to embed any warning in HTML
    warningsToBrowser(1);
    
    # define some global variables
    $users_dir = "dataset-medium";
    $debug = 1;

    #check session variables
    $logged_in = $session->param('logged_in');
    $user = $session->param('username');
    if ($logged_in == 1){
        if (defined param('logout')) {  #user wants to logout
            $session->param('logged_in', '0');  #set cookie to logged out
            login();
        } elsif (defined param('user_page')) {  #show user page
            print user_page(param('user_page'));
        } elsif (defined param('search')) { #search page
            print search(param('search'));
        } elsif (defined param('comments')) {   #comment page
            print comment_page(param('comments'));
        } elsif (defined param('make_post')) {
            print new_post(param('make_post'));
            print main_page($user);
        } elsif (defined param('make_comment')) {
            print new_comment(param('make_comment'));
            print comment_page(url_param('comments'));
        } elsif (defined param('make_reply')) {
            print new_reply(param('make_reply'));
            print comment_page(url_param('comments'));
        } elsif (defined param('mate_request')) {
            print add_mate(param('mate_request'));
            print user_page(url_param('user_page'));
        } elsif (defined param('settings')) {
            print settings_page();
        } elsif (defined param('remove')) {
            print remove_friend(param('remove'));
            print user_page($user);
        } elsif (defined param('delete_post')) {
            print delete_post(param('delete_post'));
            print user_page($user);
        } elsif (defined param('delete_account')) {
            print delete_account();
            $session->param('logged_in', '0');  #set cookie to logged out
            login();
        } elsif (defined param('edit_profile')) {
            print edit_profile();
        } elsif (defined param('profile_text')) {
            print change_info();
            print edit_profile();
        } elsif (defined param('photo')) {
            print upload_profile(param('photo'));
            print edit_profile();
        } elsif (defined param('delete_profile_pic')) {
            print delete_profile_pic();
            print edit_profile();
        } elsif (defined param('background')) {
            print upload_background(param('background'));
            print edit_profile();  
        } elsif (defined param('delete_profile_back')) {
            print delete_profile_back();
            print edit_profile();
        } else {
            print main_page($user); #show the home page, e.g recent posts, mentions.
        }
    } else {
        if (defined param('create_account')) {
            print create_account();
        } elsif (defined param('create_zid') && defined param('create_password') && defined param('create_email')) {
            print add_account();
            login();
        } elsif (login()) {  #login and check success
            print main_page($user);
        }
    }
    print page_trailer();
}

#Create session cookie
sub session {
    $session = new CGI::Session("driver:File", undef, {Directory=>'/tmp'});
    $cookie = CGI::Cookie->new(-name=>$session->name, -value=>$session->id);
}

#Login page
sub login {
	my $username = param('username') || '';
	my $password = param('password') || '';
    my $final = 0;  #0 failure 1 success
    my $error = "";
    if ($username && $password) {
        if (-e "$users_dir/$username/user.txt") {   #check if username exists
            open (F, "<", "$users_dir/$username/user.txt") or die "$0: can't open accounts/$username/password: $!\n";
            while (my $line = <F>) {
                if ($line =~ /^password/) {
                    my $temp = $line;
                    $temp =~ s/^password=//;
                    chomp ($temp);
                    if ($temp eq $password) {
                        $final = 1;
                        #create session variables
                        $session->param('logged_in', '1');
                        $session->param('username', $username);
                        $user = $session->param('username');
                        last;
                    } else {
                        $error = "Wrong password\n";
                        $final = 0;
                        print <<eof
                        $error
                        <form method="POST" action="">
                        <input type="text" name="username" maxlength="8" placeholder="Username">
                        <input type="password" name="password" placeholder="Password">
                        <input type="submit" value="Enter">
                        <a href="matelook.cgi?create_account=1">Create new account</a>
                        </form>
eof
                    }
                }
            }
        } else {
            $error = "Wrong username\n";
            $final = 0; 
            print <<eof
            $error
            <form method="POST" action="">
            <input type="text" name="username" maxlength="8" placeholder="Username">
            <input type="password" name="password" placeholder="Password">
            <input type="submit" value="Enter">
            <a href="matelook.cgi?create_account=1">Create new account</a>
            </form>
eof
        }
    } else {
        print <<eof
              $error
              <form method="POST" action="">
              <input type="text" name="username" maxlength="8" placeholder="Username">
              <input type="password" name="password" placeholder="Password">
              <input type="submit" value="Enter">
              <a href="matelook.cgi?create_account=1">Create new account</a>
              </form>
eof
    }
    return $final;  #return success or fail
}

sub main_page {
    top_row();
    my $friends_posts = "";
    my $mentioned_posts = "";
    my $mentioned_comments = "";
    my $mentioned_replies = "";
    my $current_user = $_[0];
    my @post_dir;
    my @comment_dir;
    my @reply_dir;
    $post_details = posts($current_user);   #show posts made by user and sort
    $post_details =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;  #replace zid with links
    open (F, "<", "$users_dir/$current_user/user.txt") or die "can not open $users_dir/$current_user/user.txt: $!";
    while (my $line = <F>) {
        if ($line =~ /^mates=\[(.*)\]/) {
            ($mates = $line) =~ s/^mates=\[(.*)\]/$1/;
        }
    }
    chomp $mates;
    my @mate_list = split ", ", $mates; #split to find list of mates
    close F;
    foreach my $arg (@mate_list) {  #show posts by friends
        $friends_posts .= posts($arg);
    }
    $friends_posts =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    my @mention_posts = glob("$users_dir/*/posts/*/post.txt");
    foreach my $arg (@mention_posts) {  #show posts that mention user
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line =~ /^message=/) {
                ($message = $line) =~ s/^message=(.*)/$1/;
            }
        }
        if ($message =~ /$current_user/) {
            push @post_dir, $arg;
        }
        close F;
    }
    $mention_posts = custom_posts(@post_dir);   #sort by reverse time
    $mention_posts =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    my @mention_comments = glob("$users_dir/*/posts/*/comments/*/comment.txt"); #show comments that mention user
        foreach my $arg (@mention_comments) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line =~ /^message=/) {
                ($message = $line) =~ s/^message=(.*)/$1/;
            }
        }
        if ($message =~ /$current_user/) {
            push @comment_dir, $arg;
        }
        close F;
    }
    $mention_comments = custom_posts(@comment_dir);
    $mention_comments =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    my @mention_replies = glob("$users_dir/*/posts/*/comments/*/replies/*/reply.txt");  #show replies that mention user
    foreach my $arg (@mention_replies) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line =~ /^message=/) {
                ($message = $line) =~ s/^message=(.*)/$1/;
            }
        }
        if ($message =~ /$current_user/) {
            push @reply_dir, $arg;
        }
        close F;
    }
    $mention_replies = custom_posts(@reply_dir);
    $mention_replies =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    return<<eof
<div class="matelook_altheading">
Home Page
</div>
<div class="matelook_user_details">
<div class="matelook_subheading">
Make a post:
</div>
<form method="POST" action="">
<textarea name="make_post" cols="100" rows="7"></textarea> 
<input type="submit" name="make_post" class="matelook_button">
</form>
<div class="matelook_subheading">
Your Recent Posts
</div>
$post_details
<div class="matelook_subheading">
Your Friends Posts
</div>
$friends_posts
<div class="matelook_subheading">
Your Recent Mentions
</div>
$mention_posts
<div class="matelook_subheading">
Mentioned Comments
</div>
$mention_comments
<div class="matelook_subheading">
Mentioned Replies
</div>
$mention_replies
</div>
eof
    
}

#
# Display user information and posts
# 
sub user_page {
    top_row();
    my $user_to_show = "$users_dir/$_[0]";
    my $details_filename = "$user_to_show/user.txt";
    my $image = "";
    my $post_details = "";
    if (! -d "$user_to_show") {
        return "<div class=\"matelook_user_details\"><div class=\"matelook_subheading\">\nUser not found (May be deleted or suspended)\n</div></div>";
    }
    if (-e "$user_to_show/profile.jpg") {   #check if profile pic exists
        $image = "<img src=\"$user_to_show/profile.jpg\" height=\"200\" width=\"200\">";
    } else {
        $image = "<img src=\"images/no_profile.png\" height=\"200\" width=\"200\">";    #show generic if no profile pic
    }
    open (F, "<", "$details_filename") or die "can not open $details_filename: $!";
    while (my $line = <F>) {    #remove raw text, remove <,>
        chomp $line;
        if ($line =~ /\<|\>/) {
            $line =~ s/\</&lt;/g;
            $line =~ s/\>/&gt;/g;
        }
        if ($line =~ /^courses=\[(.*)\]/) {
            ($courses = $line) =~ s/^courses=\[(.*)\]/$1/;
        } elsif ($line =~ /^email=(.*)/) {
            ($email = $line) =~ s/^email=(.*)/$1/;
        } elsif ($line =~ /^password=(.*)/) {
            ($password = $line) =~ s/^password=(.*)/$1/;
        } elsif ($line =~ /^home_latitude=(.*)/) {
            ($home_latitude = $line) =~ s/^home_latitude=(.*)/$1/;
        } elsif ($line =~ /^home_longitude=(.*)/) {
            ($home_longitude = $line) =~ s/^home_longitude=(.*)/$1/;
        } elsif ($line =~ /^home_suburb=(.*)/) {
            ($home_suburb = $line) =~ s/^home_suburb=(.*)/$1/;
        } elsif ($line =~ /^zid=(.*)/) {
            ($zid = $line) =~ s/^zid=(.*)/$1/;
        } elsif ($line =~ /^full_name=(.*)/) {
            ($full_name = $line) =~ s/^full_name=(.*)/$1/;
        } elsif ($line =~ /^program=(.*)/) {
            ($program = $line) =~ s/^program=(.*)/$1/;
        } elsif ($line =~ /^mates=\[(.*)\]/) {
            ($mates = $line) =~ s/^mates=\[(.*)\]/$1/;
        } elsif ($line =~ /^birthday=(.*)/) {
            ($birthday = $line) =~ s/^birthday=(.*)/$1/;   
        } elsif ($line =~ /^profile_text=(.*)/) {
            ($profile_text = $line) =~ s/^profile_text=(.*)/$1/;   
        }
    }
    #Allow for some html tags
    $profile_text =~ s/&lt;b&gt;/<b>/;
    $profile_text =~ s/&lt;\/b&gt;/<\/b>/;
    $profile_text =~ s/&lt;u&gt;/<u>/;
    $profile_text =~ s/&lt;\/u&gt;/<\/u>/;
    $profile_text =~ s/&lt;i&gt;/<i>/;
    $profile_text =~ s/&lt;\/i&gt;/<\/i>/;
    if ($profile_text =~ /<[bui]>/) { #Try to close some tags
        $profile_text =~ s/<([a-z])>(.*)/<$1>$2<\/$1>/g;
    }
    chomp $mates;
    my @mate_list = split ", ", $mates; #find friends
    close F;
    $post_details = posts($_[0]);   #show recent posts in profile
    my $list_size = scalar @mate_list;
    my $tempdir = "";
    foreach my $arg (@mate_list) {
        if (-e "$users_dir/$arg/profile.jpg") {
            $tempdir = "<img src=\"$users_dir/$arg/profile.jpg\" height=\"60\" width=\"60\">";
        } else {
            $tempdir = "<img src=\"images/no_profile.png\" height=\"60\" width=\"60\">";
        }
        if ($user eq $_[0]) {
            $list .= "$tempdir<a href=\"matelook.cgi?user_page=$arg\">$arg<\/a>  <a href=\"matelook.cgi?remove=$arg\">Remove friend<\/a>\n";   #add link to friends
        } else {
            $list .= "$tempdir<a href=\"matelook.cgi?user_page=$arg\">$arg<\/a>\n";
        }
    }
    $email = $email;    #stop perl from complaining
    $home_latitude = $home_latitude;    #unused variables for later
    $home_longitude = $home_longitude;
    $password = $password;
    $courses = $courses;
    $post_details =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    my $tag = "";
    if (defined param(user_page)) {
        my $curr_page = param(user_page);
        if (-e "$users_dir/$curr_page/background.jpg") {
            $tag = "<script>document.body.style.background=\"url($users_dir/$curr_page/background.jpg)\"</script>";
        }
    }
    return <<eof
<div id="matelook_user_details" class="matelook_user_details">
<div class="mate_request">
    <form method="POST" action="">
        <input type="hidden" name="mate_request" value="$zid">
        <input type="submit" value="Send mate request" class="matelook_button">
    </form>
</div>
$image
Name: $full_name
zid: $zid
Program: $program
Birthday: $birthday
Home Suburb: $home_suburb
<p>
$profile_text
<p>
<div class="matelook_subheading">
Posts
</div>
$post_details
<p>
<div class="matelook_subheading">$list_size Friends:\n</div>
$list
</div>
$tag
eof
}

#Gets posts and sorts them by reverse chronological order
#Uses str2time
sub posts {
    my @posts = glob("$users_dir/$_[0]/posts/*"); #grab user posts
    my %post;
    my $output = "";
    foreach my $arg (@posts) {
        open (F, "<", "$arg/post.txt") or die "can not open $arg/post.txt: $!";
        while (my $line = <F>) {
            chomp $line;
            if ($line =~ /^time=(.*)/) {
                ($post_time = $line) =~ s/^time=(.*)/$1/;   #grab time of post
            }
        }
        my $temp = str2time($post_time);    #convert to unix time
        $post{$temp} = "$arg/post.txt"; #create hash table linking time to dir
        close F;
    }
    foreach my $date (reverse sort keys %post) {    #reverse sort based on time
        open (F, "<", "$post{$date}") or die "can not open $post{$date}: $!";
        while (my $line = <F>) {
            $time = scalar localtime $date;
            if ($line !~ /^longitude=|^latitude=/) {    #remove raw text, personal info
                if ($line =~ /\\n/) {
                    $line =~ s/\\n/&#10;/g;    
                }
                if ($line =~ /\<|\>/) {
                    $line =~ s/\</&lt;/g;
                    $line =~ s/\>/&gt;/g;
                }
                if ($line =~ /^from=(.*)/) {
                    ($from = $line) =~ s/^from=(.*)/$1/;
                    chomp $from;
                } elsif ($line =~ /^message=(.*)/) {
                    ($message = $line) =~ s/^message=(.*)/$1/;
                    chomp $message;
                }
            }
            
        }
        $temp_comment_dir = $post{$date};
        $temp_comment_dir =~ s/$users_dir//;
        $temp_comment_dir =~ s/posts\/([0-9]+)\/.*/posts\/$1/;
        my $comment_total = count_comments($temp_comment_dir); #counts comments of a thread
        if ($from eq $user) {
            $output .= "Date Posted: $time\nFrom: $from&#10;$message&#10;<a href=\"matelook.cgi?comments=$temp_comment_dir\">$comment_total Comments<\/a>\n<a href=\"matelook.cgi?delete_post=$temp_comment_dir\">Delete<\/a>\n\n\n";
        } else {
            $output .= "Date Posted: $time\nFrom: $from&#10;$message&#10;<a href=\"matelook.cgi?comments=$temp_comment_dir\">$comment_total Comments<\/a>\n\n\n";
        }
    }
    return $output;
}

#Gets array and sorts them by reverse chronological order
#Uses str2time
#Same logic as above
sub custom_posts {
    #Get input array
    my @posts = @_;
    my %post;
    my $output = "";
    foreach my $arg (@posts) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            chomp $line;
            if ($line =~ /^time=(.*)/) {
                ($post_time = $line) =~ s/^time=(.*)/$1/;
            }
        }
        #Convert to unix time
        my $temp = str2time($post_time);
        $post{$temp} = "$arg";
        close F;
    }
    #Sort hash by time
    foreach my $date (reverse sort keys %post) {
        open (F, "<", "$post{$date}") or die "can not open $post{$date}: $!";
        while (my $line = <F>) {
            $time = scalar localtime $date;
            if ($line !~ /^longitude=|^latitude=/) {
                if ($line =~ /\\n/) {
                    $line =~ s/\\n/&#10;/g;    
                }
                if ($line =~ /\<|\>/) {
                    $line =~ s/\</&lt;/g;
                    $line =~ s/\>/&gt;/g;
                }
                if ($line =~ /^from=(.*)/) {
                    ($from = $line) =~ s/^from=(.*)/$1/;
                    chomp $from;
                } elsif ($line =~ /^message=(.*)/) {
                    ($message = $line) =~ s/^message=(.*)/$1/;
                    chomp $message;
                }
            }
            
        }
        $temp_comment_dir = $post{$date};
        #$temp_comment_dir =~ s/\/[a-z]+\.txt//;
        $temp_comment_dir =~ s/$users_dir//;
        $temp_comment_dir =~ s/posts\/([0-9]+)\/.*/posts\/$1/;
        my $comment_total = count_comments($temp_comment_dir);
        if ($from eq $user) {
            $output .= "Date Posted: $time\nFrom: $from&#10;$message&#10;<a href=\"matelook.cgi?comments=$temp_comment_dir\">$comment_total Comments<\/a>\n<a href=\"matelook.cgi?delete_post=$temp_comment_dir\">Delete<\/a>\n\n\n";
        } else {
            $output .= "Date Posted: $time\nFrom: $from&#10;$message&#10;<a href=\"matelook.cgi?comments=$temp_comment_dir\">$comment_total Comments<\/a>\n\n\n";
        }
    }
    return $output;
}

#Counts total comments
sub count_comments {
    my @comments = glob("$users_dir/$_[0]/comments/*");
    my @replies = glob("$users_dir/$_[0]/comments/*/replies/*");
    return scalar @comments + scalar @replies;
}

#Sorts posts by time
#Same logic as posts()
sub sort_posts {
    my @sorted;
    my %post;
    foreach my $arg (@_) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            chomp $line;
            if ($line =~ /^time=(.*)/) {
                ($post_time = $line) =~ s/^time=(.*)/$1/;
            }
        }
        my $temp = str2time($post_time);
        $post{$temp} = "$arg";
        close F;
    }
    foreach my $date (reverse sort keys %post) {
        push @sorted, $post{$date};
    }
    return @sorted;
}

#Shows comment thread
#Input is a zid and post number
sub comment_page {
    if (! -d "$users_dir/$_[0]") {  #check if dir exists
        return "NOTHING HERE";
    }
    top_row();
    my $post = "";
    my $replies = "";
    my $post_time;
    open (F, "<", "$users_dir/$_[0]/post.txt") or die "can not open $users_dir/$_[0]/post.txt: $!";
    while (my $line = <F>) {    #remove raw text
        if ($line !~ /^longitude=|^latitude=/) {
            if ($line =~ /\\n/) {
                $line =~ s/\\n/&#10;/g;    
            }
            if ($line =~ /^time=(.*)/) {
                ($post_time = $line) =~ s/^time=(.*)/$1/;
            }
            if ($line =~ /\<|\>/) {
                $line =~ s/\</&lt;/g;
                $line =~ s/\>/&gt;/g;
            }
            if ($line =~ /^from=(.*)/) {
                ($from = $line) =~ s/^from=(.*)/$1/;
                chomp $from;
            } elsif ($line =~ /^message=(.*)/) {
                ($message = $line) =~ s/^message=(.*)/$1/;
                chomp $message;
            }
        }
    }
    close F;
    $post_time = str2time($post_time);
    $time = scalar localtime $post_time;
    $post = "Date Posted: $time\nFrom: $from&#10;$message\n";
    my @comments = glob("$users_dir/$_[0]/comments/*/comment.txt");
    @comments = sort_posts(@comments);  
    my $count = 0;
    foreach my $arg (@comments) {   #sort comments and display comment
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line !~ /^longitude=|^latitude=/) {
                if ($line =~ /\\n/) {
                    $line =~ s/\\n/&#10;/g;    
                }
                if ($line =~ /^time=(.*)/) {
                    ($post_time = $line) =~ s/^time=(.*)/$1/;
                }
                if ($line =~ /\<|\>/) {
                    $line =~ s/\</&lt;/g;
                    $line =~ s/\>/&gt;/g;
                }
                if ($line =~ /^from=(.*)/) {
                    ($from = $line) =~ s/^from=(.*)/$1/;
                    chomp $from;
                } elsif ($line =~ /^message=(.*)/) {
                    ($message = $line) =~ s/^message=(.*)/$1/;
                    chomp $message;
                }
            }

        }
        close F;
        $post_time = str2time($post_time); #Convert gmt time to epoch
        $time = scalar localtime $post_time; #Convert epoch back to local time
        #Show reply, add toggled reply box
        $replies .= "Date Posted: $time\nFrom: $from&#10;$message
<form method=\"POST\" action=\"\">
<a href=\"javascript:showreply('reply$count')\">Reply to comment</a>
<div id=\"reply$count\" class=\"reply_submit\" style=\"display: none;\">
<textarea name=\"make_reply\" cols=\"100\" rows=\"7\"></textarea> 
<input type=\"hidden\" name=\"replydir\" value=\"$arg\">
<input type=\"submit\" name=\"make_reply\" class=\"matelook_button\">
</div>
</form>\n\n";
        ($temp_arg = $arg) =~ s/\/comment.txt$//;
        my @replies = glob("$temp_arg/replies/*/reply.txt");
        @replies = sort_posts(@replies);
        foreach my $comment (@replies) {    #sort and display reply to comment
            open (F, "<", "$comment") or die "can not open $comment: $!";
            while (my $line = <F>) {
                if ($line !~ /^longitude=|^latitude=/) {
                    if ($line =~ /\\n/) {
                        $line =~ s/\\n/&#10;&#09;/g;    
                    }
                    if ($line =~ /^time=(.*)/) {
                    ($post_time = $line) =~ s/^time=(.*)/$1/;
                    }
                    if ($line =~ /\<|\>/) {
                        $line =~ s/\</&lt;/g;
                        $line =~ s/\>/&gt;/g;
                    }
                    if ($line =~ /^from=(.*)/) {
                        ($from = $line) =~ s/^from=(.*)/$1/;
                        chomp $from;
                    } elsif ($line =~ /^message=(.*)/) {
                        ($message = $line) =~ s/^message=(.*)/$1/;
                        chomp $message;
                    }
                }
            }
            close F;
            $post_time = str2time($post_time);
            $time = scalar localtime $post_time;
            $replies .= "&#09;Reply: Date Posted: $time\n&#09;From: $from&#10;&#09;$message&#10;\n\n\n"; 
        }
        $count++;
    }
    $post =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g; #add links to zid
    $replies =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g;
    return<<eof
<div class="matelook_user_details">
<div class="matelook_subheading">
Post:
</div>
$post
<form method="POST" action="">
<textarea name="make_comment" cols="100" rows="7"></textarea> 
<input type="submit" name="make_comment" class="matelook_button">
</form>
<div class="matelook_subheading">
Comments:
</div>
$replies
</div>
eof
}

#Creates new post
sub new_post {
    if ($_[0] eq "") {
        return "<script>alert(\"Please add text\")</script>";
    }
    my $output = "alert(\"Post not added\");";
    my $count = 0;
    #Find empty dir slot
    while (-d "$users_dir/$user/posts/$count") {
        $count++;
    }
    my $new_dir = "$users_dir/$user/posts/$count";
    my $new_file = "$new_dir/post.txt";
    my $message = $_[0];
    chomp $message;
    $message =~ s/\r\n/\\n/g;   #replace new lines
    $message =~ s/\n/\\n/g;
    my $time = strftime "%FT%T+0000", gmtime $^T; #get current gmt time in correct format
    mkdir($new_dir, 0755) unless(-d $new_dir);  #make dir if it doesnt exist
    if (! -e "$new_file") {
        open(F, '>', $new_file) or die "Could not open file $new_file: $!";
        print F "from=$user\nmessage=$message\ntime=$time";
        $output = "alert(\"Post added\");"; #tell user added post
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Add comment to post, reloads back into comment page
sub new_comment {
    if ($_[0] eq "") {
        return "<script>alert(\"Please add text\")</script>";
    }
    my $output = "alert(\"Post not added\");";
    my $comment_dir = url_param('comments');
    $comment_dir =~ s/^\///;
    my $count = 0;
    mkdir("$users_dir/$comment_dir/comments", 0755) unless(-d "$users_dir/$comment_dir/comments");
    while (-d "$users_dir/$comment_dir/comments/$count") {
        $count++;
    }
    my $new_dir = "$users_dir/$comment_dir/comments/$count";
    my $new_file = "$new_dir/comment.txt";
    my $message = $_[0];
    chomp $message;
    $message =~ s/\r\n/\\n/g;   #replace new lines
    $message =~ s/\n/\\n/g;
    my $time = strftime "%FT%T+0000", gmtime $^T; #get current time gmt in correct format
    mkdir($new_dir, 0755) unless(-d $new_dir);  #make dir if it doesnt exist
    if (! -e "$new_file") {
        open(F, '>', $new_file) or die "Could not open file $new_file: $!";
        print F "from=$user\nmessage=$message\ntime=$time";
        $output = "alert(\"Comment added\");"; #tell user added post
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Add reply to comment, reloads back into comment page
sub new_reply {
    if ($_[0] eq "") {
        return "<script>alert(\"Please add text\")</script>";
    }
    my $reply_dir = param("replydir");
    $reply_dir =~ s/\/\//\//;
    $reply_dir =~ s/\/comment\.txt/\/replies/;
    my $output = "alert(\"Post not added\");";
    my $count = 0;
    mkdir($reply_dir, 0755) unless(-d $reply_dir);
    while (-d "$reply_dir/$count") {
        $count++;
    }
    my $new_dir = "$reply_dir/$count";
    my $new_file = "$new_dir/reply.txt";
    my $message = $_[0];
    chomp $message;
    $message =~ s/\r\n/\\n/g;   #replace new lines
    $message =~ s/\n/\\n/g;
    my $time = strftime "%FT%T+0000", gmtime $^T; #get current gmt time in correct format
    mkdir($new_dir, 0755) unless(-d $new_dir);  #make dir if it doesnt exist
    if (! -e "$new_file") {
        open(F, '>', $new_file) or die "Could not open file $new_file: $!";
        print F "from=$user\nmessage=$message\ntime=$time";
        $output = "alert(\"Reply added\");"; #tell user added post
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Add search bar
#Adds hidden submit button
sub search_bar {
    return <<eof
<div class="search_bar">
<form method="POST" action="">
Search: <input type="text" name="search">
<input type="submit" style="visibility: hidden; position: absolute;" />
</form>
</div>
eof
}

#Searches for users and posts
sub search {
    top_row();
    my $search = $_[0];
    my $mate_result = "";
    my $tempsearch;
    my $tempdir;
    #Replace <,>
    $search =~ s/\</&lt;/g;
    $search =~ s/\>/&gt;/g;
    my @posts = sort(glob("$users_dir/*/user.txt")); #user list
    foreach my $arg (@posts) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line =~ /^zid=/) { #find zid
                ($search_id = $line) =~ s/^zid=(.*)/$1/;
            }
        }
        seek F,0,0;
        while (my $line = <F>) {
            if ($line =~ /^full_name=/) {   #find full name and compare
                ($full_name = $line) =~ s/^full_name=(.*)/$1/;
                my $tempname = $1;
                chomp $full_name;
                chomp $search;
                chomp $search_id;
                if ($full_name =~ /\Q$search/i) {   #ignore symbols, case
                    ($tempdir = $arg) =~ s/\/user.txt/\/profile.jpg/;
                    #if no profile picture show default image
                    if (-e "$tempdir") {
                        $mate_result .= "<a href=\"matelook.cgi?user_page=$search_id\"><img src=\"$tempdir\" height=\"60\" width=\"60\">$tempname: $search_id</a>\n";
                    } else {
                        $mate_result .= "<a href=\"matelook.cgi?user_page=$search_id\"><img src=\"images/no_profile.png\" height=\"60\" width=\"60\">$tempname: $search_id</a>\n";       
                    }
                }
            }
        }
    }
    my @search_posts = glob("$users_dir/*/posts/*/post.txt"); #search posts for search term
    foreach my $arg (@search_posts) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {
            if ($line =~ /^message=/) {
                ($message = $line) =~ s/^message=(.*)/$1/;
            }
        }
        if ($message =~ /\Q$search/i && $search ne "") {
            push @post_dir, $arg;
        }
        close F;
    }
    $post_result = custom_posts(@post_dir);   #sort by reverse time
    my $size = scalar @post_dir;
    my $count = 0;
    #Adds pagination
    #Adds divs every 16 results
    #By default all hidden except for first
    $post_result =~ s/^/<div id=\"$count\" class=\"search_pages\" style=\"display: block;\">/;
    $post_result =~ s/(s<\/a>)/(++$count % 16 == 0) ? "s<\/a>&#10;&#10;<a href=\"javascript:nextpage('$count')\">Next page<\/a>
    <a href=\"javascript:prevpage('$count')\">Previous page<\/a>
    <\/div><div id=\"$count\" class=\"search_pages\" style=\"display: none;\">" : $1/ge;
    my $temp = $size%16;    #Find last div
    $size = $size - $temp +16;
    #Adds final prevpage link
    $post_result .= "<a href=\"javascript:prevpage('$size')\">Previous page<\/a></div>";
    $post_result =~ s/([^\/])(z[0-9]{7})/$1<a href="matelook.cgi?user_page=$2">$2<\/a>/g; #Replace zid with links
    return<<eof
<div class="matelook_user_details">
You searched for: $search
Results found:
<div class="matelook_subheading">
Users:
</div>
$mate_result
<div id="results" class="matelook_subheading">
Posts:
</div>
$post_result
</div>
eof
}

#Add mate to list
sub add_mate {
    my $mate = $_[0];
    my $output = "alert(\"$mate not added\");";
    if ($mate eq $user) {   #If adding themselves
        return "<script>alert(\"You cannot add yourself\");</script>";
    }
    open (F, "<", "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
    while (my $line = <F>) {
        if ($line =~ /^mates=/) {
            ($mates = $line) =~ s/^mates=\[(.*)\]/$1/;
        }
    }
    chomp $mates;
    chomp $mate;
    my @mate_list = split ", ", $mates;
    foreach my $friend (@mate_list) {  #Check if mate added before
        if ($friend eq $mate) {
            return "<script>alert(\"Mate already added\");</script>";
        }
    }
    seek F,0,0;
    my @lines;
    while (my $line = <F>) {    #Add to mate list
        if ($line =~ /^mates=/) {
            if ($line =~ /^mates=\[\]/) { #if no mates before adding
                $line =~ s/\]$/$mate\]/;
            } else {
                $line =~ s/\]$/, $mate\]/;
            }
        }
        push @lines, $line;
    }
    close F;
    #Manually delete and then create new file
    #Using some perl modules broke the header
    unlink "$users_dir/$user/user.txt";
    if (! -e "$users_dir/$user/user.txt") {
        open (F, '>', "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
        foreach $arg (@lines) {
            print F "$arg";
        }
        $output = "alert(\"$mate added\");";
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Show settings page
sub settings_page {
    top_row();
    return<<eof
<div class="matelook_user_details">
<br>
<a href=\"javascript:deleteacc()\">Delete Account<\/a>
<br><br>
</div>    
eof
}

#Removes selected friend
#Only should be accessed when on own user page
sub remove_friend {
    my $mate = $_[0];
    my $output = "alert(\"$mate not removed\");";
    my $mate_exists = 0;
    open (F, "<", "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
    my @lines;
    while (my $line = <F>) {
        #find mate list
        if ($line =~ /^mates=/) {
            if ($line =~ /^mates=\[$mate, /) {  #if mate is the first in list
                $line =~ s/$mate, //;
            } elsif ($line =~ /^mates=\[$mate\]/) { #if mate is the only one in list
                $line =~ s/$mate//;
            } else {
                $line =~ s/, $mate//;   
            }
        }
        push @lines, $line;
    }
    close F;
    #Manually delete and then create new file
    #Using some perl modules broke the header
    unlink "$users_dir/$user/user.txt";
    if (! -e "$users_dir/$user/user.txt") {
        open (F, '>', "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
        foreach $arg (@lines) {
            print F "$arg";
        }
        $output = "alert(\"$mate removed\");";
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Adds new account to dataset
sub add_account {
    my $output = "alert(\"Account not created\")";
    my $zid = param('create_zid') || '';
	my $password = param('create_password') || '';
    my $email = param('create_email') || '';
    if ($zid eq "") {   #If zid field is empty
        return "<script>alert(\"No zid given\")</script>";
    }
    if ($password eq "") {
        return "<script>alert(\"No password given\")</script>";
    }
    if ($email eq "") {
        return "<script>alert(\"No email given\")</script>";
    }
    #Check if zid is in correct format
    if ($zid !~ /z[0-9]{7}/) {
        return "<script>alert(\"zid not in correct format\")</script>";
    }
    my @accounts = glob("$users_dir/*/user.txt"); #user list
    foreach my $arg (@accounts) {
        open (F, "<", "$arg") or die "can not open $arg: $!";
        while (my $line = <F>) {    #Get email and zid from file
            if ($line =~ /^email=(.*)/) {
                ($temp_email = $line) =~ s/^email=(.*)/$1/;
            } elsif ($line =~ /^zid=(.*)/) {
                ($temp_zid = $line) =~ s/^zid=(.*)/$1/;
            }
        }
        chomp $temp_zid;
        chomp $temp_email;
        #Check if zid has been used
        if ($temp_zid eq $zid){
            return "<script>alert(\"zid already used\")</script>";
        }
        #Check if email has been used
        if ($email eq $temp_email){
            return "<script>alert(\"Email already used\")</script>";
        }
    }
    #Set up account directories
    mkdir("$users_dir/$zid", 0755) unless (-d "$users_dir/$zid");
    mkdir("$users_dir/$zid/posts", 0755) unless (-d "$users_dir/$zid/posts");
    #Create new user.txt
    if (! -e "$users_dir/$zid/user.txt") {
        open (F, ">", "$users_dir/$zid/user.txt") or die "can not open $users_dir/$zid/user.txt: $!";
        print F "email=$email\nzid=$zid\npassword=$password\nmates=[]\n";
        close F;
        $output = "alert(\"Account created\")";
    }
    return<<eof
<script>
$output
</script>
eof
}

#Prints the create account page
sub create_account {
    return<<eof
<div class="matelook_user_details">
<div class="matelook_subheading">
Create new account
</div>
<br>
<form method="POST" action="">
    <label for="txtzid">zid:</label><input type="text" name="create_zid" maxlength="8"><br><br>
    <label for="txtpassword">Password:</label><input type="password" name="create_password"><br><br>
    <label for="txtemail">Email:</label><input type="text" name="create_email"><br><br>
    <input type="submit" value="Submit" class="matelook_button">
</form>
</div>
eof
}

#Edit profile info
#Also includes uploading forms for profile picture/background.
sub edit_profile {
    top_row();
    return<<eof
<div class="matelook_user_details">
<div class="matelook_altheading">
Edit profile
</div>
<form method="POST" action="">
    <label for="profiletext">Profile Text:</label><input type="text" name="profile_text"><br><br>
    <label for="nametext">Name:</label><input type="text" name="edit_name"><br><br>
    <label for="programtext">Program:</label><input type="text" name="edit_program"><br><br>
    <label for="suburbtext">Suburb:</label><input type="text" name="edit_suburb"><br><br>
    <label for="emailtext">Email:</label><input type="text" name="edit_email"><br><br>
    <label for="passwordtext">Password:</label><input type="password" name="edit_password"><br><br>
    <input type="submit" value="Submit" class="matelook_button"><br><br>
</form>
<form method="POST" action="" enctype="multipart/form-data">
    Upload Profile Picture: <input type="file" name="photo"><br><br>
    <input type="submit" value="Submit" class="matelook_button">
</form>
<br>
<form method="POST" action="">
    Delete Profile Picture: <br><input type="hidden" name="delete_profile_pic" class="matelook_button">
    <input type="submit" value="Delete" class="matelook_button">
</form>
<br><br>
<form method="POST" action="" enctype="multipart/form-data">
    Upload Profile Background: <input type="file" name="background"><br><br>
    <input type="submit" value="Submit" class="matelook_button">
</form>
<br><br>
<form method="POST" action="">
    Delete Profile Background: <br><input type="hidden" name="delete_profile_back" class="matelook_button">
    <input type="submit" value="Delete" class="matelook_button">
</form>
<br><br>
</div>
eof
}

#Change personal info
sub change_info {
    #Get info from params
	my $text = param('profile_text') || '';
	my $name = param('edit_name') || '';
    my $program = param('edit_program') || '';
	my $suburb = param('edit_suburb') || '';
    my $email = param('edit_email') || '';
    my $password = param('edit_password') || '';
    my $output = "alert(\"Profile info not changed\")";
    #Create new hash which checks if info has been changed or not
    my %check = (
    "text"  => 0,
    "name" => 0,
    "program"  => 0,
    "suburb"  => 0,
    "email"  => 0,
    "password"  => 0,
    );
    open (F, "<", "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
    my @lines;
    #Change info and push into new array
    #Checks if param is not empty
    while (my $line = <F>) {
        if ($line =~ /^profile_text=/ && $text ne '') {
            $line =~ s/^profile_text=(.*)/profile_text=$text/;
            $check{text} = 1;
        } elsif ($line =~ /^full_name=/ && $name ne '') {
            $line =~ s/^full_name=(.*)/full_name=$name/;
            $check{name} = 1;
        } elsif ($line =~ /^home_suburb=/ && $suburb ne '') {
            $line =~ s/^home_suburb=(.*)/home_suburb=$suburb/;
            $check{suburb} = 1;
        } elsif ($line =~ /^program=/ && $program ne '') {
            $line =~ s/^program=(.*)/program=$program/;
            $check{program} = 1;
        } elsif ($line =~ /^email=/ && $email ne '') {
            $line =~ s/^email=(.*)/email=$email/;
            $check{email} = 1;
        } elsif ($line =~ /^password=/ && $password ne '') {
            $line =~ s/^password=(.*)/password=$password/;
            $check{password} = 1;
        }
        push @lines, $line;
    }
    #If the original info did not exist push onto end of array
    foreach my $arg (keys %check) {
        if ($arg eq "text" && $check{$arg} == 0 && $text ne '') {
            push @lines, "profile_text=$text\n";
        } elsif ($arg eq "name" && $check{$arg} == 0 && $name ne '') {
            push @lines, "full_name=$name\n";
        } elsif ($arg eq "suburb" && $check{$arg} == 0 && $suburb ne '') {
            push @lines, "home_suburb=$suburb\n";
        } elsif ($arg eq "program" && $check{$arg} == 0 && $program ne '') {
            push @lines, "program=$program\n";
        } elsif ($arg eq "email" && $check{$arg} == 0 && $email ne '') {
            push @lines, "email=$email\n";
        } elsif ($arg eq "password" && $check{$arg} == 0 && $password ne '') {
            push @lines, "password=$password\n";
        }
    }
    close F;
    #Manually delete and then create new file
    #Using some perl modules broke the header
    unlink "$users_dir/$user/user.txt";
    if (! -e "$users_dir/$user/user.txt") {
        open (F, '>', "$users_dir/$user/user.txt") or die "can not open $users_dir/$user/user.txt: $!";
        foreach my $arg (@lines) {
            print F "$arg";
        }
        $output = "alert(\"Profile info changed\");";
        close F;
    }
    return<<eof
<script>
$output
</script>
eof
}

#Delete profile picture
sub delete_profile_pic {
    my $output = "alert(\"Profile picture not deleted (May not exist)\")";
    if (-e "$users_dir/$user/profile.jpg") { #if image exists delete it
        unlink "$users_dir/$user/profile.jpg";
        $output = "alert(\"Profile picture deleted\")";
    }
    return<<eof
<script>
$output
</script>
eof
}

#Deletes profile background
sub delete_profile_back {
    my $output = "alert(\"Profile background not deleted (May not exist)\")";
    if (-e "$users_dir/$user/background.jpg") { #if image exists delete it
        unlink "$users_dir/$user/background.jpg";
        $output = "alert(\"Background picture deleted\")";
    }
    return<<eof
<script>
$output
</script>
eof
}

#Uploads profile picture
sub upload_profile {
    #if image exists delete it
    if (-e "$users_dir/$user/profile.jpg") {
        unlink "$users_dir/$user/profile.jpg";
    }
    my $filename = $_[0];
    my $output = "alert(\"Profile picture not changed\")";
    my $upload_dir = "$users_dir/$user";
    #Open new file handle and print uploaded image to it
    open (LOCAL, ">", "$upload_dir/profile.jpg") or die "can not open $upload_dir/profile.jpg: $!";
    binmode LOCAL;
    while (<$filename>) {
        print LOCAL $_;
    }
    $output = "alert(\"Profile picture changed\")";
    close LOCAL;
    return<<eof
<script>
$output
</script>
eof
}

#Uploads profile background
sub upload_background {
    if (-e "$users_dir/$user/background.jpg") { #if image exists delete it
        unlink "$users_dir/$user/background.jpg";
    }
    my $filename = $_[0];
    my $output = "alert(\"Profile background not changed\")";
    my $upload_dir = "$users_dir/$user";
    #Open new file handle and print uploaded image to it
    open (LOCAL, ">", "$upload_dir/background.jpg") or die "can not open $upload_dir/background.jpg: $!";
    binmode LOCAL;
    while (<$filename>) {
        print LOCAL $_;
    }
    $output = "alert(\"Profile background changed\")";
    close LOCAL;
    return<<eof
<script>
$output
</script>
eof
}

#Deletes posts made by user
sub delete_post {
    my $output = "alert(\"Post not deleted\")";
    my $temp = $_[0];
    my $match = $temp;
    $match =~ s/\/(z[0-9]{7})\/posts\/.*/$1/;
    if ($user !~ /$1/) {    #If the current user does not match post author
        return "<script>alert(\"Cannot delete post not created by you\")</script>";
    }
    my $dir = "$users_dir$temp";
    if (-d "$dir") {
        rmtree($dir);   #Delete folder
        $output = "alert(\"Post deleted\")";
    }
    return<<eof
<script>
$output
</script>
eof
}

#Deletes account
sub delete_account {
    my $output = "alert(\"Account not deleted\")";
    #Get acc dir
    my $dir = "$users_dir/$user";
    if (-d "$dir") {    #Check if dir exists
        rmtree($dir);
        $output = "alert(\"Account deleted\")";
    }
    return<<eof
<script>
$output
</script>
eof
}

#Add top row items
sub top_row {
    print logout();
    print "<a href=\"matelook.cgi?settings=1\">Settings</a> ";
    print "<a href=\"matelook.cgi?edit_profile=1\">Edit Profile</a>";
    print search_bar();
}

#Adds logout button
#Shows who your are logged in as
sub logout {
    return <<eof
Logged in as <a href="matelook.cgi?user_page=$user">$user</a>

<div class="logout">
<form method="POST" action="">
    <input type="submit" name="logout" value="Logout" class="matelook_button">
</form>
</div>
eof
}

#
# HTML placed at the top of every page
#
sub page_header {
    
    return <<eof
Content-Type: text/html;charset=utf-8

<!DOCTYPE html>
<html lang="en">
<meta http-equiv="set-cookie" content="$cookie">
<head>
<title>matelook</title>
<link href="matelook.css" rel="stylesheet">
<link rel="shortcut icon" href="images/favicon.png">
</head>
<body>
<div class="matelook_heading">
<a href="matelook.cgi?main_page" style="text-decoration:none; color:inherit;">matelook</a>
</div>
eof
}

#
# HTML placed at the bottom of every page
# It includes all supplied parameter values as a HTML comment
# if global variable $debug is set
#
sub page_trailer {
    my $html = "";
    $html .= join("", map("<!-- $_=".param($_)." -->\n", param())) if $debug;
    $html .= end_html;
    #Javascript functions below
    #Showreply toggles the reply box div
    #Prevpage/nextpage displays the next page div, while hiding the current page div
    return <<eof
<script type="text/javascript">
    //Toggles reply box
    function showreply(input) {
        var div = document.getElementById(input);
        if (div.style.display !== 'none') {
            div.style.display = 'none';
        }
        else {
            div.style.display = 'block';
        }
    }
    
    //Show next page
    //Hide current div of search results, and show next 16 results
    //Scrolls back up to top
    function nextpage(input) {
        document.getElementById(input).style.display = 'block';
        var next = input;
        next -= 16;
        document.getElementById(next).style.display = 'none';
        document.getElementById('results').scrollIntoView();
    }
    
    //Show previous page
    //Hide current div of search results, and show previous 16 results
    //Scrolls back up to top
    function prevpage(input) {
        var last = input;
        last -= 16;
        //If on first page, alert user
        if (last == 0) {
            alert("First page");
        } else {
            document.getElementById(last).style.display = 'none';
            var previous = last;
            previous -= 16;
            document.getElementById(previous).style.display = 'block';
            document.getElementById('results').scrollIntoView();
        }
    }
    
    //Gives confirmation to deleting account
    function deleteacc(input) {
        if (confirm('Are you sure you want to delete your account?\\n(This cannot be reversed)')) {
            document.location = "matelook.cgi?delete_account=1";
        } else {

        }
    }
</script>    
$html
eof
}

main();
