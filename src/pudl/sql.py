from typing import Any, TypeVar, cast, override
from string.templatelib import Template

from pudl.column_base import ColumnBase
from pudl.table_base import TableBase


class SQLTemplate:
    def __call__(self, template_obj: Any) -> str:
        if not isinstance(template_obj, Template):
            raise TypeError(f"Expected Template, got {type(template_obj)}")

        result_parts: list[str] = []

        # Iterate over template components
        for item in template_obj:
            if isinstance(item, str):
                result_parts.append(item)
            else:
                value = item.value

                # Check if it's a TableBase subclass (not instance)
                if isinstance(value, type) and issubclass(value, TableBase):
                    result_parts.append(value.fqn())
                # Check if it's a ColumnBase instance
                elif isinstance(value, ColumnBase):
                    result_parts.append(value.info.fqn)
                else:
                    raise Exception(f"Unexpected interpolation type: {type(cast(Any, value))}")

        result = "".join(result_parts)
        return result


T = TypeVar("T")


class SQLQuery:
    def __init__(self, template_str: Any):
        self.template_str: Any = template_str

    def execute(self) -> str:
        return SQLTemplate()(self.template_str)


class SQL:
    def __getitem__(self, return_type: type[T]) -> type:
        # Return a callable that creates SQLQuery with the type attached
        class TypedSQLQuery(SQLQuery):
            @override
            def execute(self) -> str:
                return super().execute()

        return TypedSQLQuery

    def __call__(self, template_str: Any) -> SQLQuery:
        return SQLQuery(template_str)


# class SQL:
#     def __getitem__(self, return_type: type[T]) -> SQLTemplate[T]:
#         return SQLTemplate(return_type)
#
#     def __call__(self, template_str: Any) -> str:
#         return SQLTemplate(str)(template_str)


sql = SQL()
#
#
# # Example usage
# if __name__ == "__main__":
#     # Example implementations
#     class MyTable(TableBase): ...
#
#     class MyColumn(ColumnBase): ...
#
#     foo = sql[bool](t"Table FQN: {MyTable}")
