from typing import Any, Dict
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """
    Universal base model for all external APIs.
    
    - Write all fields in snake_case (Python convention)
    - Accepts both camelCase and snake_case input (populate_by_name=True)
    - Use to_json_camel() for camelCase APIs (e.g., Shopify)
    - Use to_json_snake() for snake_case APIs (e.g., Slack)
    
    Nested Accessors:
        Define __nested_accessors__ class variable to automatically create
        properties for nested attributes:
        
        class SlackUser(ApiModel):
            profile: SlackUserProfile
            
            __nested_accessors__ = {
                'email': 'profile.email',
                'display_name': 'profile.display_name',
            }
        
        # Now you can use:
        user.email = "new@example.com"  # Sets profile.email
    
    Example:
        class Order(ApiModel):
            order_id: str
            customer_name: str
        
        # Accepts both formats
        order = Order(orderId='123', customerName='Joe')
        order = Order(order_id='123', customer_name='Joe')
        
        # Serialize for Shopify (camelCase)
        order.to_json_camel()  # '{"orderId":"123","customerName":"Joe"}'
        
        # Serialize for Slack (snake_case)
        order.to_json_snake()  # '{"order_id":"123","customer_name":"Joe"}'
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra='ignore'
    )
    
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """
        Called by Pydantic after the model class is fully configured.
        Creates properties for nested accessors defined in __nested_accessors__.
        """
        super().__pydantic_init_subclass__(**kwargs)
        
        if hasattr(cls, '__nested_accessors__'):
            nested_accessors = getattr(cls, '__nested_accessors__')
            if isinstance(nested_accessors, dict):
                for accessor_name, model_path in nested_accessors.items():
                    def getter(self, path=model_path) -> Any:
                        """Get the nested attribute value."""
                        obj = self
                        for attr in path.split('.'):
                            obj = getattr(obj, attr)
                        return obj
                    
                    def setter(self, value: Any, path=model_path) -> None:
                        """Set the nested attribute value."""
                        parts = path.split('.')
                        obj = self
                        for attr in parts[:-1]:
                            obj = getattr(obj, attr)
                        setattr(obj, parts[-1], value)
                    
                    setattr(cls, accessor_name, property(getter, setter))
    
    def to_json_camel(self) -> str:
        """
        Serialize to JSON string with camelCase keys.
        Use for APIs like Shopify GraphQL.
        
        Returns:
            JSON string with camelCase keys
        """
        return self.model_dump_json(by_alias=True)
    
    def to_json_snake(self) -> str:
        """
        Serialize to JSON string with snake_case keys.
        Use for APIs like Slack.
        
        Returns:
            JSON string with snake_case keys
        """
        return self.model_dump_json(exclude_none=True)
    
    def to_dict_snake(self) -> Dict[str, Any]:
        """
        Serialize to dict with snake_case keys, excluding None values.
        Use for APIs like Slack when you need a dict instead of JSON string.
        
        Returns:
            Dict with snake_case keys, None values excluded
        """
        return self.model_dump(exclude_none=True)
