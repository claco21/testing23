// priority: 0

ServerEvents.recipes(event => {event.shaped(
  Item.of('backpacked:backpack', 1), // arg 1: output
  [
    'AAA',
    'BCB', // arg 2: the shape (array of strings)
    'ADA'
  ],
  {
    A: 'minecraft:leather',
    B: 'minecraft:string',  //arg 3: the mapping object
    C: 'minecraft:iron_ingot',
	D: 'minecraft:chest'
  }
)

  console.log('Hello! The recipe event has fired!')
})