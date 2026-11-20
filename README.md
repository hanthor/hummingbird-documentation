# hanthor/hummingbird-documentation

A mirror of <https://gitlab.com/redhat/hummingbird/documentation>, read-only
from GitLab. It is not an official Hummingbird repository, and nothing syncs
it automatically. Branches other than this one (`mirror-info`) and `utah/*`
are upstream's, as of the last refresh.

It stages Project Bluefin Utah's Secure Boot proposals as GitHub pull requests
against the mirrored `main`, for Hummingbird maintainers to review. The
canonical place to merge anything is still GitLab.

Refresh (updates upstream branches and tags; keeps `mirror-info`, `utah/*` and open PR branches):

```bash
git clone --mirror https://gitlab.com/redhat/hummingbird/documentation.git /tmp/hb-documentation.git && git -C /tmp/hb-documentation.git push --force https://github.com/hanthor/hummingbird-documentation.git 'refs/heads/*:refs/heads/*' 'refs/tags/*:refs/tags/*'
```
