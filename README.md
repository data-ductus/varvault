# README

## TL;DR
### Introduction
A Python library for storing and using variables from a Python process in a global context and saving the variables to a file for being reused and/or debugging.  

### Install
```
pip3 install varvault
```

### Contact
calle.holst@dataductus.se


## What is this? 
This is a package that allows you to create a key-value vault for storing variables in a global context. It allows 
you to set up a keyring with pre-defined constants which act as keys for the vault. These constants are then what is 
stored inside the vault. A key is just a string, but the value that the key is mapped to can be assigned to any type of 
object in Python. If the object is serializable (like a list or a dict), it can also be writen to something like a JSON file.    
You can then use a decorator to annotate functions that you want to have use this vault to either store return variables 
in or to extract variables to be used as input for the function.  

## How does it work? 
The way this works is that when you write a function, you annotate it with a special decorator (`varvault.Vault.vaulter`)
that takes some arguments. This decorator will then handle any input arguments and return variables for you.
The decorator takes some arguments that defines certain keys and flags to tweak the behavior.

### How about an example?
The best examples can be found in the test suites which can give a very good idea how it works and is guaranteed to be up-to-date. 
```python
import varvault


class Keyring(varvault.Keyring):
    arg1 = varvault.Key("arg1", valid_type=int)
    arg2 = varvault.Key("arg2", valid_type=int)


vault = varvault.create(keyring=Keyring, resource=varvault.JsonResource("~/test.json", mode=varvault.ResourceModes.WRITE))


@vault.vaulter(return_keys=[Keyring.arg1, Keyring.arg2])
def create_args(arg1, arg2):
    return arg1, arg2


@vault.vaulter(input_keys=[Keyring.arg1, Keyring.arg2])
def use_args(arg1: int = varvault.AssignedByVault, arg2: int = varvault.AssignedByVault):
    print(f"{Keyring.arg1}: {arg1}, {Keyring.arg2}: {arg2}")


def run_create_args():
    create_args(1, 2)
    

def run_use_args():
    use_args()


if __name__ == "__main__":
    run_create_args()
    
    run_use_args()    
```
1. In this example, we start by creating a class that defines a keyring. This keyring will be the keys used
   in the vault. Any key you use for storing variables or take variables out should be defined as a constant 
   in this keyring (by default, this is the way to use it, but it is possible to be more flexible).

2. Then we create the actual Vault-object. It's entirely possible to create a Vault without using the factory function,
   but the factory function will do some things for you to make it slightly easier. Creating the vault requires only
   a single argument to be defined and that is a class that inherits from the `varvault.Keyring` (a class based on the Keyring class here).
   Optionally, you can define some flags to further tweak the behavior of the vault. These tweaked behaviors include
   allowing for existing key-value pairs to be modified (this is not allowed by default), allowing return variables from
   functions defined with return keys to be None, and setting a flag to write some additional debug logs.
   We also define the input parameter `resource` which is a `varvault.JsonResource` object that points to a `.JSON` file. This resource will be used  
   as a vault file to store all the arguments in. 

3. We define a function called `create_args` that takes some arguments (we have to insert variables
   into the vault somehow, right?) that we annotate with the vault decorator. We pass an argument to the
   decorator called `return_keys`. This argument tells the vault which keys this function will assign its
   return variables to. Note that the order of the return keys matter. In this case, the ingoing argument `arg1` will
   be assigned to `Keyring.arg1`, and the ingoing argument `arg2` will be assigned to `Keyring.arg2`. It's very possible
   to set `return_keys` to a single `Key` as well if you only have one variable to return. If you want more control
   over how return variables are handled, please see `varvault.MiniVault` and make use of that to ensure that
   return-variables are handled exactly as you want. 
   
   **Note:** When this function is called, and it finishes, the decorator here will capture the return variables and then store 
   those return variables in the vault with the keys that were passed to the decorator as `return_keys`. These variables can then be 
   accessed by another function that uses the same vault-object as this one does to decorate a function.

4. We then create a new function called `use_args` that we also annotate with the vault decorator. We pass a different
   argument to the decorator this time called `input_keys`. This argument tells the vault which keys in the vault
   we want passed to this function. The order of the keys doesn't really matter here, the order is mostly aesthetic.
   
   **Note:** What ends up happening when this function is called, is that the decorator will try to extract keys defined in
   `input_keys` from the vault and then pass those variables to the function as a dictionary (by defining the arguments as
   keyword arguments, these arguments won't need to be provided when the method is called). 
   It is possible to just bundle all the arguments in the signature of the function as a `**kwargs` structure (in this case the signature
   would be `def use_args(**kwargs)`). One of the benefits of doing like in the example is that you can easily see what 
   arguments will be provided by the vault when you use the function, so you know which arguments you have to provide and which are provided by the vault.

5. We create a very simple function called `run_create_args` which doesn't get annotated. This function is simply made
   to demonstrate what makes this vault so useful. When this function is called, it will obviously call `create_args`,
   which will assign variables to `Keyring.arg1` and `Keyring.arg2` which will then be stored in the vault.

6. A final function called `run_use_args` is then created which calls the `use_args` function. This function
   is able to use the arguments defined in `create_args` because with this vault, the context for where a function runs
   doesn't really matter as long as the input variables it needs exists in the vault-object already, and the function
   exists in that scope.

7. Lastly, the variables that were involved in the execution of this code can be viewed by simply checking the contents 
   of the file `~/test.json`. In this example the file would simply contain: 
   ```
   {
     "arg1": 1,
     "arg2": 2
   }
   ```
8. When a file such as this (see above) exists, it's very possible to re-create the same vault again from this file. 
   In order to re-create the same vault again simply do this: 
   ```python
   import varvault

   class Keyring(varvault.Keyring):
       arg1 = varvault.Key("arg1")
       arg2 = varvault.Key("arg2")
      
   vault = varvault.create(varvault.Flags.permit_modifications, 
                           keyring=Keyring,                           
                           resource=varvault.JsonResource("~/test.json", mode=varvault.ResourceModes.APPEND))
   ```
   When re-creating a vault from an existing file it's recommended to allow modifications 
   (see `varvault.VaultFlags.permit_modifications`) in-case you are planning to write the same
   arguments to the vault again. 

## Conclusion
This README demonstrates what this functionality can be used for. With this vault, the context for where
a function executes doesn't matter as long as the keys the function require have been assigned in the vault and the
functions exists in the scope. The functions become building blocks that you can call regardless of context provided
the above criteria have been met. You don't need to clutter your main function calls with tons of input variables being passed around 
because all of that is handled for you by the vault and the decorator. If you use it correctly, you can end up with
functions that on the surface appears to not use any arguments or pass any return variables at all. This makes the main
body of your code clean and easy to follow. It allows you to focus on the actual logic of your code instead of having to necessarily having to 
bother with the context for where the code runs. Setting a variable in one function and using that variable in another function is simply a matter of 
setting it and using it without passing it around from one function to another. 

By using this functionality, you can create a vault that can be used in any context, and you can use the vault to
store variables that are used in multiple functions. This is very useful when you have a lot of functions that need to
use the same variables at different depths of your code. 

Adding new input variables or return variables to a function is very easy, because you don't need to think about how
the function is used, as long as the variables you need exist. Varvault handles all input variables and return 
variables for you, simply within the context of the function itself. As long as variables already exist in the vault, 
passing a variable to a function is simply a matter of adding the variable to the function signature as a keyword argument.
If a variable doesn't yet exist in the vault, varvault will scream at you telling you that you're doing something wrong, and you need to reconsider. 

The keys in the Keyring allows you to see where your keys are actually being used. By saving arguments to a file or a database, 
it allows you to keep parts of the context the code ran in previously. This can be very useful when deploying something which 
then has to be un-deployed at a later time that isn't necessarily running in the same process as before. By saving the context to a file, 
it becomes very easy to debug your code since you can see every variable that you assigned to varvault.
Varvault essentially adds an extra layer similar to environment variables that is infinitely more complex since you can assign 
anything you your keys, not just string. Since the arguments can be saved to something like a JSON file, 
anything that can parse JSON can obviously use the data as they see fit. 
