# Oracle voting foundation

This package contains a pure voting calculation only. It is not an Oracle service,
market-data client, prediction generator, archive, MCP server, or execution veto.
It has no network, wallet, or order capability. It must not be connected to an
executor until an integration validates the provenance, instrument, horizon,
strategy version, and prospective timing of every input.

`aggregate` accepts up to 14 current strategy votes for one instrument and horizon.
The caller supplies a positive minimum number of resolved calls. A vote below 60%
accuracy, without enough resolved calls, issued in the future, or expired is
excluded. Excluded strategies must still be evaluated by the future evidence owner.
Duplicate identities and malformed evidence raise `ValueError`. If no eligible
votes remain, the result is unavailable. The function cannot verify whether input
counts or timestamps are authentic.

Each eligible weight is hits divided by resolved calls; more than 100 hits doubles
the total weight. This is a provisional interpretation of the owner's request, not
a measured advantage. Flat votes contribute weight to the denominator. Signed
balance is 100 times the sum of directional weights divided by total weight.
Balance at or above 60 is Strong Buy; at or above 20 is Buy; at or below -60 is
Strong Sell; at or below -20 is Sell; otherwise it is Flat. These display thresholds
are provisional. Balance is agreement, not a calibrated probability or profit
forecast. The caller owns the meaning and evidence of resolved outcomes.

Run the isolated checks from the repository root:

```sh
python3 -m unittest discover -s oracle/tests -t . -v
```
