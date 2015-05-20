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
<td>/data/mtm/table</td><td>GET DELETE for MtM, PUT not supported</td>
</tr>
<tr>
<td>/data/table/PKColumn/value</td><td>GET PUT DELETE</td>
</tr>
<tr>
<td>/data/table</td> <td>POST for any table</td>
</tr>
<tr>
<td>/data/table/filter</td><td>GET PUT DELETE for non-MtM</td>
</tr>
</p>

<p>All required parameters for these methods are passed via JSON (even for MtM GET)</p>
<p>The reason for separating many-to-many tables is ORM logic</p>