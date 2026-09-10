from ctg_go.modules.audit import models as audit_models  # noqa: F401
from ctg_go.modules.clients import models as clients_models  # noqa: F401
from ctg_go.modules.cpe import models as cpe_models  # noqa: F401
from ctg_go.modules.gestions import models as gestions_models  # noqa: F401
from ctg_go.modules.identity import models as identity_models  # noqa: F401


def import_models() -> None:
    """Import side effects so SQLAlchemy metadata is fully registered."""
