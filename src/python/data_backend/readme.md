<p>
About those symlinks.
<br/>
Relative import in python works strange.
<br/>
With symlinks at least it works, but looks ugly.
</p>

<p>
ROLES:
1. REST-wrapper for postresql/pgpool2 queries
</p>

<p>
API:
<br/>
<table>
<tr>
<td>/data/table</td><td>POST for any table</td>
</tr>
<tr>
<td>/data/table/PKColumn/value</td><td>GET PUT DELETE for non-compound PK</td>
</tr>
<tr>
<td>/data/table/filter</td><td>GET PUT DELETE for any table</td>
</tr>
</p>

<p>All required parameters for these methods are passed via JSON (even for MtM GET)</p>
<p>The reason for separating many-to-many tables is ORM logic</p>