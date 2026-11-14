# Third-party notices

Version: 0.1.0
Delta: Initial source attribution for the supported jsonalias dependency.

## jsonalias 0.1.1

Executor and SolTUI support solders 0.27.1, whose package metadata requires
jsonalias exactly 0.1.1. That published artifact omits license metadata and a
bundled license file. Upstream added the following MIT license at commit
`2a98db9c4024b1914f198f088f2aaa15a8cd7423`, when its project version was 0.1.2.
The installed 0.1.1 module is byte-identical to the module at that commit.

Source project:
https://github.com/kevinheavey/jsonalias

Immutable license:
https://github.com/kevinheavey/jsonalias/blob/2a98db9c4024b1914f198f088f2aaa15a8cd7423/LICENSE

Identical source module:
https://github.com/kevinheavey/jsonalias/blob/2a98db9c4024b1914f198f088f2aaa15a8cd7423/jsonalias/__init__.py

- Module SHA256: `35a9a4b543e6f08ad0f8f7f91d0ed53cbd7e0f7925a4aeab5cf52b2e6cfa6db1`.
- License-text SHA256: `002c2696d92b5c8cf956c11072baa58eaf9f6ade995c031ea635c6a1ee342ad1`.
- License addition: 2022-10-30; the 0.1.1 wheel was published on 2022-10-28.

Retain the upstream notice when redistributing this dependency. Its copyright
line is reproduced exactly, including the upstream placeholders. This notice
records the source provenance; it does not rewrite the published 0.1.1 artifact
or establish license clearance for every optional dependency or distribution.
The supported solders pin remains unchanged.

```text
MIT License

Copyright (c) [year] [fullname]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Audit evidence: `.cdo/reviews-2026-11-12/dependency-supplement.json`.
