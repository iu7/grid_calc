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
<td>ENDPOINT</td> <td>DESCRIPTION</td> <td>INPUT</td> <td>RESPONCE</td>
</tr>
<tr>
  <td>/data/table</td>
  <td>POST for any table</td>
  <td>your_object</td>
  <td>
    <table>
      <tr><td>METHOD</td> <td>EC</td> <td>JSON</td></tr>
      <tr><td>ANY</td> <td>200</td> <td>your_object</td></tr>
      <tr><td>ANY</td> <td>400/500</td> <td>{"error" : string_message }</td></tr>
    </table>
  </td>
</tr>
<tr>
  <td>/data/table/PKColumn/value</td>
  <td>GET PUT DELETE for non-compound PK</td>
  <td>
    <table>
      <tr><td>METHOD</td> <td>INPUT</td></tr>
      <tr><td>GET, DELETE</td> <td>---</td></tr>
      <tr><td>PUT</td> <td>changes_object</td></tr>
    </table>
  </td>
  <td>
    <table>
      <tr><td>METHOD</td> <td>EC</td> <td>JSON</td></tr>
      <tr><td>GET</td> <td>200</td> <td>your_requested_object</td></tr>
      <tr><td>PUT</td> <td>200</td> <td>your_modified_object</td></tr>
      <tr><td>DELETE</td> <td>200</td> <td>{}</td></tr>
      <tr><td>ANY</td> <td>400/404/500</td> <td>{"error" : string_message }</td></tr>
    </table>
  </td>
</tr>
<tr>
  <td>/data/table/filter</td>
  <td>GET PUT DELETE for any table</td>
  <td>
    <table>
      <tr><td>METHOD</td> <td>INPUT</td></tr>
      <tr><td>GET, DELETE</td> <td>{field1 : value1, ..., fieldN : valueN} -- kinda filter</td></tr>
      <tr><td>PUT</td> <td>{field1 : value1, ..., fieldN : valueN, "changes" : changes_object}</td></tr>
    </table>
  </td>
  <td>
    <table>
      <tr><td>METHOD</td> <td>EC</td> <td>JSON</td></tr>
      <tr><td>PUT, DELETE</td> <td>200</td> <td>{"count" : int} -- rows affected</td></tr>
      <tr><td>GET</td> <td>200</td> <td>{[object1, ... , objectN]]}</td></tr>
      <tr><td>ANY</td> <td>400/404/500</td> <td>{"error" : string_message }</td></tr>
    </table>
  </td>
</tr>
</table>
</p>
<p>GENERAL NOTICE: 400 is usually returned for insufficient input, 500 for postgres error, 404 obvious.</p>
