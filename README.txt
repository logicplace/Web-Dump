==== Basic Use ====
Run program for help file. This mentions the flags and command line syntax.
Alternatively (or additionally) you may pipe commands into the program from
a file or what have you.
When piping, all options are separated by newlines, and the URL *must* be the
first line of the input (ie. you *cannot* specify it on the command line).
Additional lines in the input are options akin to:
-o xyz
**Important** Each option must be on its own line!
It is not recommended to use the -c option in the file.
Options passed via the command line take precedence over ones sent by pipe.

==== URL Syntax ====
Give a standard URL, replacing the dynamic sections with counters.
Counters are formatted as so:
 1) Start with a percent (%)
 2) Optional: Formatting section
 2a) Optional: Hyphen (-) Forces padding on the right of the number instead of
     left 2b takes precedence over this. If you wish to right-pad the default
     character, you will have to enter the default character in 2b manually.
 2b) Optional: Character to pad with. May only be one character.
 2c) Width as a number, default is 1.
 3) Name
 4) Optional: How-To-Count section, these may be in any order. All are optional
 4a) Order, preceded by an exclamation mark (!) Order starts at 1.
     Alternatively, you may use !l to state this is linked, ie. the counter
     howto is elsewhere (identified by the same name).
     By default, this is the counter index in the url, left to right.
 4b) 404 tolerance, preceded by an asterisk (*) If this many HTTP errors are
     returned, it will move to the next counter.
     Alternatively, you may use *f to state that failures are expected and it
     should instead move on when 200 (success) is returned.
     By default, there is infinite tolerance.
 4c) Custom digit sequence, surrounded by brackets ([ and ]) If you need to
     count something other than numbers, you can pass it this way.
     In addition to raw characters, you may express ranges, for instance:
     [0-9a-f] would represent lowercase hexadecimal.
     If you want you use a literal hyphen or backslash, you will have to escape
     it with a backslash (\): 
     [\-\\] being a binary system where 0 is - and 1 is \
     If you wish there to be no 0 at all (just that tens, hundreds, etc. digits
     simply don't exist, rather than are 0) use an asterisk (*) at the
     beginning of the range. If you want a literal asterisk for the 0th digit,
     you may escape the asterisk with a backslash like above.
     Examples:
      [a-f]    b, c, ..., f, ba, bb
      [*a-f]   a, b, ..., f, aa, ab
      [\*a-f]  a, b, ..., f, a*, aa
      [\\*a-f] \, *, ..., f, *\, **
     Any invalid ranges or blackslashes will be treated literally.
     By default this is decimal, ie. [0123456789]
 4d) Range, surrounded by braces ({ and }) You supply the starting index and
     the ending value separated by a comma. Both are individually optional.
     Example: {0,10} means this counter starts at 0, and stops after 10. If
     used with [01] then this will only be three attempted downloads.
     Default starting is the first digit (by digit's default, 1)
     Default ending is infinity
     Therefore, default with no custom digit sequence is {1,}
 4e) Add a + to say that this counter should not reset when it fails, and only
     incriment the next counter.
     Alternatively, use a minus sign (-) to do the same but also reset the
     counter to the first attempt that failed in the current failure sequence.
     Example: You have counters %a!2; and %b!1*1+; and it goes something like
     this
      [a:1,b:1] , [a:1,b:2] , [a:1,b:3] (404s!) , [a:2,b:3] , [a:2,b:4] , ...
     Example for %a!2; and %b!1*2-;
      [a:1,b:1] , [a:1,b:2] (404s!) , [a:1.b:3] , [a:1,b:4] (404s!) ,
      [a:1,b:5] (404s!) , [a:2,b:4] , [a:2,b:5] , ...
     However, the counter will restart if it reaches the max, regardless of the
     existence of + or -
 5) End with a semicolon (;)

==== Search URL Syntax ====
This is just regex. If you need regex help try http://regular-expressions.info
If you are searching for more than just the url, you can indicate which group
is the url by appending | then the group number, eg. |1
Group 0 is the default.

==== Filename Syntax ====
When specifying a custom filename, you can use parts 1 through 3 from the URL
syntax specification. That is, the percent (%), formatting, and name. No
semicolon.
If you supplied a search URL, you can address the groups you made in that with
a pound sign (#) followed by the group number.
The special sequence #i and group 0 (ie. #0) refer to the index of the match on
the page. The first match is 0 and the second is 1 and so-on.

==== Continue Syntax ====
When using the continue option, specify the counters and their starting
position in the form: NAME : STARTING
Separate each counter by commas.
Example: a:1,b:2 starts counter a at 1 and b at 2
If you don't specify a counter it will use its default starting value.
The special name "link" will indicate which link in the list to start from,
0-based.
Generally you won't need to know this but I figured it'd be good to mention!

==== Changelog ====
v4 Rewrote from scratch
 * Now allows \ and * as the 0th and 1st digits with another \ prefix, ie. [\\*]
 * Added #i and #0 in filename as being the index of the link found on the page
 * Added group selector for scanning
v3 Added the return variation of no-reset (-)
 * Fixed a bug with how 404 tolerance was handled
 * Fixed a bug that caused a counter to not max out if it had been increased
   by the previous counter 404ing
v2 Added the no-reset howto. (+)
 * Added Continue Syntax to readme.
v1 Initial release
 * Included is "oreimo.txt", an example file that downloads Ore no Imouto from 
   Manga Fox, specifically written for Chen.
 * "formatting.txt" is a technical document, describing counter syntax.
