title: Web App Security
author: Stavros Korokithakis
description: A primer on web app security
date: <%= Date.today %>
% available themes: Default - Sky - Beige - Simple - Serif - Night - Moon - Solarized
theme: solarized
% available transitions: // default/cube/page/concave/zoom/linear/fade/none
transition: cube
code-engine: coderay
code-line-numbers: inline

# Web App Security

## (and how to break it, I guess?)

!SLIDE

## What is security?

!SLIDE

## SQL Injection

<ul>
<li class="fragment"><code>query = "SELECT * FROM users WHERE username=" + username + " and password=" + password + ";"</code></li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment"><strong>Wrong.</strong> You're fucked.</li>
</ul>

!SLIDE

## Cross-site scripting (XSS)

<ul>
<li class="fragment"><code>&lt;a onclick="show_hello('{ user.name }')"&gt;click me&lt;/a&gt;</code></li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment"><strong>Wrong.</strong> You're fucked.</li>
</ul>

!SLIDE

## Cross-site request forgery (CSRF)

<ul>
<li class="fragment"><code>def delete_story(request, story_id): if user.is_admin(): Story.get(story_id).delete() </code></li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment"><strong>Wrong.</strong> You're fucked.</li>
</ul>

!SLIDE

## Session fixation

<ul>
<li class="fragment"><code>www.mysite.com/welcome/?sessid=SOMELONGSESSID</code></li>
<li class="fragment">User browses anonymously with the session ID, and when they authenticate, we remember it by storing their username in the session.</li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment"><strong>Wrong.</strong> You're fucked.</li>
</ul>

!SLIDE

## Session hijacking

<ul>
<li class="fragment">Store a user session ID in a cookie and use it to identify them, rather than send session data with every request.</li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment">That one actually is reasonable. You're still fucked, though.</li>
</ul>

!SLIDE

## Path traversal

<ul>
<li class="fragment"><code>return open("userfiles/" + request.GET.filename).read()</code></li>
<li class="fragment">The user picks a file in a specific directory to read, and we show it to them</li>
<li class="fragment">Looks reasonable, right?</li>
<li class="fragment"><strong>Wrong.</strong> You're fucked.</li>
</ul>

!SLIDE

## A panacea

The CSP header.

<ul>
<li class="fragment"><code>Content-Security-Policy: default-src https://cdn.example.net; child-src 'none'; object-src 'none'</code></li>
<li class="fragment">Can tell the browser where resources are allowed to be loaded from.</li>
<li class="fragment">Governs whether inline scripts or styles will be allowed.</li>
<li class="fragment">Governs whether <code>eval()</code> will be allowed.</li>
<li class="fragment">And lots more, only for $19.95!</li>
</ul>

!SLIDE

## Passwords

<ul>
<li class="fragment"><code>database.insert(username, password)</code></li>
<li class="fragment">What are you, insane?</li>
<li class="fragment">Alright, we'll hash it. <code>database.insert(username, sha1(password))</code></li>
<li class="fragment"><strong>Wrong.</strong> Fucked again.</li>
<li class="fragment">Fine, let's use a salt. <code>database.insert(username, sha1(salt + password))</code></li>
<li class="fragment">Fucked.</li>
<li class="fragment">Jeez. <code>database.insert(username, bcrypt(password))</code></li>
<li class="fragment">Now let's check it...</li>
<li class="fragment"><code>if bcrypt(submitted_password) == stored_hash: return True</code></li>
<li class="fragment"><strong>Wrong.</strong> Super fucked.</li>
</ul>

!SLIDE

## Implementing your own cryptography

*Don't implement your own cryptography!* It is definitely going to be fifty shades of broken. Use a respected library
with as high-level primitives as you can find. NaCl, TweetNaCl are good.

# Thank you!

## Questions?

# Drinks

## Location: Terra Antiqua

<iframe src="https://www.google.com/maps/embed?pb=!1m29!1m12!1m3!1d3028.3042180350317!2d22.9517047982878!3d40.62317247705374!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!4m14!1i0!3e6!4m5!1s0x14a838e2ed0619c7%3A0xc5f92674a9aa7a21!2scoho+-+the+coworking+home%2C+Stratigou+Napoleontos+Zerva+10%2C+Thessaloniki%2C+Greece!3m2!1d40.621131999999996!2d22.955198!4m5!1s0x14a83902850282f3%3A0xec2825d3810794b9!2zVGVycmEgQW50aXF1YSBBcnQgQ2FmZSDOnM6_z4XPg861zq_OvywgTWFub2xpIEFuZHJvbmlrb3UsIFRoZXNzYWxvbmlraSA1NDYgMjE!3m2!1d40.625212999999995!2d22.952938!5e0!3m2!1sen!2s!4v1426690647692" width="800" height="500" frameborder="0" style="border:0"></iframe>
