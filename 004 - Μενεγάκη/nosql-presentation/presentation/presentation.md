title: SQL vs NoSQL
author: Stavros Korokithakis
description: A breakdown of SQL vs NoSQL databases
date: <%= Date.today %>
% available themes: Default - Sky - Beige - Simple - Serif - Night - Moon - Solarized
theme: solarized
% available transitions: // default/cube/page/concave/zoom/linear/fade/none
transition: cube
code-engine: coderay
code-line-numbers: inline

# SQL vs NoSQL

## The showdown


# About me

<p class="fragment">
<img src="portrait.jpg" /><br>
Angry Stavros is watching you.
</p>

# Summary

* SQL details
* NoSQL details
* Which is better?


!SLIDE down-open
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# SQL

## The ACID properties

<ul>
<li class="fragment"><strong>Atomicity</strong><br>
Transactions are all-or-nothing.
</li>
<li class="fragment"><strong>Consistency</strong><br>
Database state will always be valid.
</li>
<li class="fragment"><strong>Isolation</strong><br>
Transactions are always equivalent to serial.
</li>
<li class="fragment"><strong>Durability</strong><br>
Once a transaction has been committed, it's persisted.
</li>
</ul>

# SQL

## Schemas

SQL databases have them.

# SQL

## Relationality

SQL databases offer strong guarantees on this.

# SQL

## Scalability

SQL databases don't have it.

!SLIDE down-close
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

!SLIDE down-open
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# NoSQL

There is no such thing!

Things shouldn't be defined by what they are not.

# NoSQL

## ACID

Various databases have various implementations of this, also depending on scalability.

# NoSQL

## Schemas

There are various types of storage models:

* Document
* Graph
* Key-value
* Columnar

# NoSQL

## Relationality

NoSQL databases don't usually offer it.

# NoSQL

## Scalability

There's a lot of that!

!SLIDE down-close
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# Which is better?

<p class="fragment">Drumroll please...</p>

<p class="fragment">What the hell, haven't you learnt anything?<br>Use the right tool for the job!</p>

<p class="fragment">Usually, SQL databases are a great way to start until you know you need something more.</p>

<p class="fragment">Mongo sucks.</p>

!SLIDE down-open
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# Considerations

## What type of data do we need to store?

<ul>
    <li class="fragment">Relations in the data are a strong hint that you need a relational DB.</li>
    <li class="fragment">Do you need the structure of the stored data to be fixed and guaranteed?</li>
    <li class="fragment">How about the type?</li>
</ul>

# Considerations

## What stage are we at?

<ul>
    <li class="fragment">Are we prototyping our app?</li>
    <li class="fragment">Are we writing the first version of the app, that needs to be up and running quickly and with few bugs?</li>
    <li class="fragment">Are we past the initial stage and now need to scale the app as much as possible?</li>
    <li class="fragment">No, we are not.</li>
</ul>

# Considerations

## How valuable is the data?

<ul>
    <li class="fragment">How much data can we afford to lose?</li>
    <li class="fragment">Do we have another, canonical data store (i.e. is this our cache)?</li>
    <li class="fragment">How sure do we want to be that written data has been persisted?</li>
</ul>

# Considerations

## How fast do we need it to be?

<ul>
    <li class="fragment">Do we need to support a specific throughput?</li>
    <li class="fragment">How about a specific latency?</li>
    <li class="fragment">Is this a cache, or meant to speed another DBMS up?</li>
</ul>

# Considerations

## Does it need to be distributed?

<ul>
    <li class="fragment">Do we need multiple read-only machines?</li>
    <li class="fragment">How about read-write?</li>
    <li class="fragment">Do we need to propagate state across datacenters?</li>
</ul>

!SLIDE down-close
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

# Thank you!

# Questions?

# Part 3: Drinks

## Location: Terra Antiqua

<iframe src="https://www.google.com/maps/embed?pb=!1m29!1m12!1m3!1d3028.3042180350317!2d22.9517047982878!3d40.62317247705374!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!4m14!1i0!3e6!4m5!1s0x14a838e2ed0619c7%3A0xc5f92674a9aa7a21!2scoho+-+the+coworking+home%2C+Stratigou+Napoleontos+Zerva+10%2C+Thessaloniki%2C+Greece!3m2!1d40.621131999999996!2d22.955198!4m5!1s0x14a83902850282f3%3A0xec2825d3810794b9!2zVGVycmEgQW50aXF1YSBBcnQgQ2FmZSDOnM6_z4XPg861zq_OvywgTWFub2xpIEFuZHJvbmlrb3UsIFRoZXNzYWxvbmlraSA1NDYgMjE!3m2!1d40.625212999999995!2d22.952938!5e0!3m2!1sen!2s!4v1426690647692" width="800" height="500" frameborder="0" style="border:0"></iframe>
